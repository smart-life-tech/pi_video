import RPi.GPIO as GPIO
import subprocess
import random
import time
import os

# === Configuration ===
BUTTON_GPIO = 17  # Video trigger button
SHUTDOWN_GPIO = 27  # Shutdown button
VIDEO_FOLDER = "/home/pi-five/pi_video"  # Folder containing video files
VIDEO_FILES = [
    "video1.mp4",
    "video2.mp4",
    "video3.mp4"
]
BOOT_SOUND_FILE = "/home/pi-five/pi_video/boot_sound.wav"  # Sound to play on boot
BLACK_SCREEN_VIDEO = "/home/pi-five/pi_video/black.mp4"  # Black screen video file

# === Setup ===
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(SHUTDOWN_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# === Utility Functions ===
def play_video(file_name):
    full_path = os.path.join(VIDEO_FOLDER, file_name)
    if not os.path.exists(full_path):
        print(f"Video file not found: {full_path}")
        return

    print(f"Playing: {full_path}")
    
    # Kill VLC more aggressively and wait
    subprocess.call(["pkill", "-9", "-f", "vlc"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.1)
    
    # Start video immediately with minimal interface
    subprocess.call([
        "cvlc", "--fullscreen", "--no-osd", "--play-and-exit",
        "--no-video-title-show", "--no-mouse-events", "--no-keyboard-events",
        "--intf=dummy", "--no-video-deco", "--no-embedded-video",
        "--aout=alsa", "--alsa-audio-device=hw:1,0",
        "--gain=1.0", "--volume=256",
        full_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def play_boot_sound():
    if os.path.exists(BOOT_SOUND_FILE):
        print("Playing boot sound")
        subprocess.Popen([
            "cvlc", "--play-and-exit", "--no-osd",
            "--aout=alsa", "--alsa-audio-device=hw:1,0",
            "--gain=1.0", "--volume=256",
            BOOT_SOUND_FILE
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print("Boot sound file not found")

def show_black_screen_loop():
    if os.path.exists(BLACK_SCREEN_VIDEO):
        print("Starting black screen loop")
        return subprocess.Popen([
            "cvlc", "--fullscreen", "--no-video-title-show", "--no-osd",
            "--loop", "--no-audio", "--no-mouse-events", "--no-keyboard-events",
            "--intf=dummy", "--no-video-deco", "--no-embedded-video",
            BLACK_SCREEN_VIDEO
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print("Black screen video not found")
        return None

# === Main Loop ===
try:
    # Set audio to HDMI at startup
    os.system("amixer cset numid=3 2")
    
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

            # Keep black screen running while we prepare the video
            selected_video = random.choice(VIDEO_FILES)
            print(f"Selected video: {selected_video}")
            
            # Only kill black screen right before starting video
            if black_process:
                black_process.terminate()
                black_process.wait()
            
            # Start video immediately
            play_video(selected_video)

            # Restart black screen immediately after video ends
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
