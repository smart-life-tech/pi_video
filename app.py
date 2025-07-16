import RPi.GPIO as GPIO
import subprocess
import random
import time
import os

# === Configuration ===
BUTTON_GPIO = 17  # Video trigger button
SHUTDOWN_GPIO = 27  # Shutdown button
VIDEO_FOLDER = "/home/pi-five/pi_video"  # Folder containing video files
MERGED_VIDEO = "/home/pi-five/pi_video/merged_videos.mp4"  # Single merged video
BOOT_SOUND_FILE = "/home/pi-five/pi_video/boot_sound.wav"  # Sound to play on boot
BLACK_SCREEN_VIDEO = "/home/pi-five/pi_video/black.mp4"  # Black screen video file

# Video segments from video_timings.txt
VIDEO_SEGMENTS = [
    {"name": "video1", "start": 0, "duration": 45.9},
    {"name": "video2", "start": 45.9, "duration": 42.2},
    {"name": "video3", "start": 88.0, "duration": 22.9},
]

# === Setup ===
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(SHUTDOWN_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# === Utility Functions ===
def play_video_segment(segment_name):
    """Play a specific segment from the merged video"""
    if not os.path.exists(MERGED_VIDEO):
        print(f"Merged video not found: {MERGED_VIDEO}")
        return

    # Find the segment
    segment = None
    for seg in VIDEO_SEGMENTS:
        if seg["name"] == segment_name:
            segment = seg
            break
    
    if not segment:
        print(f"Segment not found: {segment_name}")
        return
    
    start_time = segment["start"]
    duration = segment["duration"]
    stop_time = start_time + duration
    
    print(f"Playing: {segment_name} from {start_time}s for {duration}s")
    #subprocess.call(["pkill", "-f", "vlc"])
    
    subprocess.call([
        "cvlc", "--fullscreen", "--no-osd", "--play-and-exit",
        "--aout=alsa", "--alsa-audio-device=hw:0,0",
        f"--start-time={start_time}",
        f"--stop-time={stop_time}",
        MERGED_VIDEO
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def play_boot_sound():
    if os.path.exists(BOOT_SOUND_FILE):
        print("Playing boot sound")
        subprocess.Popen([
            "cvlc", "--play-and-exit", "--no-osd",
            "--aout=alsa", "--alsa-audio-device=hw:1,0",
            BOOT_SOUND_FILE
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print("Boot sound file not found")

def show_black_screen_loop():
    if os.path.exists(BLACK_SCREEN_VIDEO):
        print("Starting black screen loop")
        return subprocess.Popen([
            "cvlc", "--fullscreen", "--no-video-title-show", "--no-osd",
            "--loop", "--no-audio", BLACK_SCREEN_VIDEO
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print("Black screen video not found")
        return None

# === Main Loop ===
try:
    play_boot_sound()
    black_process = show_black_screen_loop()
    print("System ready. Waiting for video button press...")
    video_playing = False

    while True:
        # Handle Shutdown Button
        if GPIO.input(SHUTDOWN_GPIO) == GPIO.LOW:
            print("Shutdown button pressed. Shutting down...")
            time.sleep(2)
            if GPIO.input(SHUTDOWN_GPIO) == GPIO.LOW:
                os.system("sudo shutdown -h now")

        # Handle Video Button
        if GPIO.input(BUTTON_GPIO) == GPIO.LOW and not video_playing:
            print("Video trigger pressed")
            video_playing = True

            if black_process:
                black_process.terminate()
                black_process.wait()

            # Randomly select a video segment
            segment_index = random.randint(0, len(VIDEO_SEGMENTS) - 1)
            selected_segment = VIDEO_SEGMENTS[segment_index]
            print(f"Selected: {selected_segment['name']}")
            
            # Play the selected segment
            play_video_segment(selected_segment['name'])

            black_process = show_black_screen_loop()
            video_playing = False

            while GPIO.input(BUTTON_GPIO) == GPIO.LOW:
                time.sleep(0.1)
            time.sleep(0.3)

        time.sleep(0.1)

except KeyboardInterrupt:
    print("Exiting program...")

finally:
    GPIO.cleanup()
    print("Cleaning up GPIO...")
