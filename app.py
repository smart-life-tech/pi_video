import RPi.GPIO as GPIO
import subprocess
import random
import time
import os
import threading

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
# ALSA HDMI device (from `aplay -l`) => card 1, device 0
env = os.environ.copy()
env['AUDIODEV'] = 'hw:1,0'
# === Setup ===
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(SHUTDOWN_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# === Global Variables ===
current_video_process = None
black_screen_process = None
current_segment = None
system_running = True

def kill_all_vlc():
    """Kill all VLC processes"""
    try:
        subprocess.call(["pkill", "-f", "vlc"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.5)
    except:
        pass

def play_video_segment(segment_name):
    """Play a specific segment from the merged video"""
    global current_video_process, current_segment
    
    if not os.path.exists(MERGED_VIDEO):
        print(f"Merged video not found: {MERGED_VIDEO}")
        return None

    # Find the segment
    segment = None
    for seg in VIDEO_SEGMENTS:
        if seg["name"] == segment_name:
            segment = seg
            break
    
    if not segment:
        print(f"Segment not found: {segment_name}")
        return None
    
    current_segment = segment
    start_time = segment["start"]
    duration = segment["duration"]
    stop_time = start_time + duration
    
    print(f"Playing: {segment_name} from {start_time}s for {duration}s")
    
    # Kill any existing video process
    if current_video_process:
        try:
            current_video_process.terminate()
            current_video_process.wait(timeout=1)
        except:
            current_video_process.kill()
    
    # Start new video process
    env = os.environ.copy()
    env['DISPLAY'] = ':0'
    
    current_video_process = subprocess.Popen([
        "cvlc", "--fullscreen", "--no-osd", "--play-and-exit",
        "--aout=alsa", "--alsa-audio-device=hw:0,0",
        f"--start-time={start_time}",
        f"--stop-time={stop_time}",
        "--intf", "dummy",
        MERGED_VIDEO
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    
    return current_video_process

def show_black_screen():
    """Show black screen loop"""
    global black_screen_process
    
    if not os.path.exists(BLACK_SCREEN_VIDEO):
        print("Black screen video not found")
        return None
    
    # Kill any existing black screen process
    if black_screen_process:
        try:
            black_screen_process.terminate()
            black_screen_process.wait(timeout=1)
        except:
            black_screen_process.kill()
    
    print("Starting black screen loop")
    
    env = os.environ.copy()
    env['DISPLAY'] = ':0'
    
    black_screen_process = subprocess.Popen([
        "cvlc", "--fullscreen", "--no-video-title-show", "--no-osd",
        "--loop", "--no-audio", "--intf", "dummy",
        BLACK_SCREEN_VIDEO
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    
    return black_screen_process

def switch_to_random_video():
    """Switch to a random video"""
    global current_segment
    
    # Stop black screen
    if black_screen_process:
        try:
            black_screen_process.terminate()
            black_screen_process.wait(timeout=1)
        except:
            black_screen_process.kill()
    
    # Select random video (avoid repeating same video)
    available_videos = VIDEO_SEGMENTS.copy()
    if current_segment:
        available_videos = [seg for seg in available_videos if seg["name"] != current_segment["name"]]
    
    if available_videos:
        selected_segment = random.choice(available_videos)
        print(f"Switching to: {selected_segment['name']}")
        
        # Play the selected segment
        play_video_segment(selected_segment['name'])
        
        # Set up timer to return to black screen after video ends
        timer = threading.Timer(selected_segment['duration'], return_to_black_screen)
        timer.daemon = True
        timer.start()

def return_to_black_screen():
    """Return to black screen after video ends"""
    global current_video_process, current_segment
    
    print("Video finished, returning to black screen")
    
    # Stop current video
    if current_video_process:
        try:
            current_video_process.terminate()
            current_video_process.wait(timeout=1)
        except:
            current_video_process.kill()
        current_video_process = None
    
    current_segment = None
    
    # Show black screen
    show_black_screen()

def cleanup_all():
    """Clean up all processes"""
    global system_running, current_video_process, black_screen_process
    
    print("Cleaning up all processes...")
    system_running = False
    
    # Stop current video
    if current_video_process:
        try:
            current_video_process.terminate()
            current_video_process.wait(timeout=2)
        except:
            current_video_process.kill()
    
    # Stop black screen
    if black_screen_process:
        try:
            black_screen_process.terminate()
            black_screen_process.wait(timeout=2)
        except:
            black_screen_process.kill()
    
    # Final cleanup
    kill_all_vlc()

def play_boot_sound():
    """Play boot sound"""
    if os.path.exists(BOOT_SOUND_FILE):
        print("Playing boot sound")
        env = os.environ.copy()
        env['DISPLAY'] = ':0'
        
        subprocess.Popen([
            "cvlc", "--play-and-exit", "--no-osd",
            "--aout=alsa", "--alsa-audio-device=hw:1,0",
            "--intf", "dummy",
            BOOT_SOUND_FILE
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)

def check_processes():
    """Check if processes are still running"""
    global current_video_process, black_screen_process, current_segment
    
    # Check if video process finished
    if current_video_process and current_video_process.poll() is not None:
        print("Video process finished")
        current_video_process = None
        current_segment = None
        # Start black screen if not already running
        if not black_screen_process or black_screen_process.poll() is not None:
            show_black_screen()
    
    # Check if black screen process died
    if black_screen_process and black_screen_process.poll() is not None:
        if not current_video_process:  # Only restart if no video is playing
            print("Black screen process died, restarting...")
            show_black_screen()

# === Main Loop ===
try:
    # Set display environment
    os.environ['DISPLAY'] = ':0'
    
    # Kill any existing VLC processes
    kill_all_vlc()
    
    # Play boot sound
    play_boot_sound()
    time.sleep(2)
    
    # Start with black screen
    show_black_screen()
    
    print("System ready. Press button to switch videos...")
    
    button_last_state = GPIO.HIGH
    last_button_time = 0
    debounce_delay = 0.3

    while system_running:
        current_time = time.time()
        
        # Handle Shutdown Button
        if GPIO.input(SHUTDOWN_GPIO) == GPIO.LOW:
            print("Shutdown button pressed. Shutting down...")
            time.sleep(2)
            if GPIO.input(SHUTDOWN_GPIO) == GPIO.LOW:
                cleanup_all()
                os.system("sudo shutdown -h now")

        # Handle Video Button with debouncing
        button_current_state = GPIO.input(BUTTON_GPIO)
        
        if (button_current_state == GPIO.LOW and 
            button_last_state == GPIO.HIGH and 
            current_time - last_button_time > debounce_delay):
            
            last_button_time = current_time
            print("Button pressed - switching to random video")
            switch_to_random_video()
        
        button_last_state = button_current_state
        
        # Check process status
        check_processes()
        
        time.sleep(0.05)

except KeyboardInterrupt:
    print("Exiting program...")

finally:
    cleanup_all()
    GPIO.cleanup()
    print("Cleanup complete!")
