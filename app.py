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

# === Setup ===
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(SHUTDOWN_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# === Global Variables ===
current_video_process = None
black_screen_process = None
current_segment = None
system_running = True
black_screen_failed = False
last_black_screen_attempt = 0

def get_audio_device():
    """Detect the correct audio device"""
    try:
        # Try to get audio devices
        result = subprocess.run(['aplay', '-l'], capture_output=True, text=True)
        output = result.stdout
        print(f"Audio devices: {output}")
        
        # Look for HDMI or default device
        if 'HDMI' in output:
            return "hw:1,0"  # Usually HDMI
        else:
            return "hw:0,0"  # Default device
    except:
        return "hw:0,0"  # Fallback

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
    
    audio_device = get_audio_device()
    
    current_video_process = subprocess.Popen([
        "cvlc", "--fullscreen", "--no-osd", "--play-and-exit",
        "--aout=alsa", f"--alsa-audio-device={audio_device}",
        f"--start-time={start_time}",
        f"--stop-time={stop_time}",
        "--intf", "dummy",
        MERGED_VIDEO
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    
    return current_video_process

def show_black_screen():
    """Show black screen with better error handling"""
    global black_screen_process, black_screen_failed, last_black_screen_attempt
    
    # Prevent rapid restart attempts
    current_time = time.time()
    if current_time - last_black_screen_attempt < 5:
        return black_screen_process
    
    last_black_screen_attempt = current_time
    
    # Kill any existing black screen process
    if black_screen_process:
        try:
            black_screen_process.terminate()
            black_screen_process.wait(timeout=1)
        except:
            black_screen_process.kill()
        black_screen_process = None
    
    # Check if black screen video exists and is valid
    if not os.path.exists(BLACK_SCREEN_VIDEO):
        print(f"Black screen video not found: {BLACK_SCREEN_VIDEO}")
        black_screen_failed = True
        return None
    
    # Try to get file info
    try:
        result = subprocess.run(['file', BLACK_SCREEN_VIDEO], capture_output=True, text=True)
        print(f"Black screen file info: {result.stdout}")
    except:
        pass
    
    if not black_screen_failed:
        print("Starting black screen with video file")
        
        env = os.environ.copy()
        env['DISPLAY'] = ':0'
        
        # Try with more compatible VLC options
        black_screen_process = subprocess.Popen([
            "cvlc", 
            "--fullscreen", 
            "--no-video-title-show", 
            "--no-osd",
            "--loop", 
            "--no-audio",
            "--intf", "dummy",
            "--vout", "gl",  # Try OpenGL output
            BLACK_SCREEN_VIDEO
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        
        # Check if it started successfully
        time.sleep(2)
        if black_screen_process.poll() is not None:
            # Get error output
            stdout, stderr = black_screen_process.communicate()
            print(f"Black screen failed. stdout: {stdout.decode()}")
            print(f"Black screen failed. stderr: {stderr.decode()}")
            black_screen_failed = True
            black_screen_process = None
    
    if not black_screen_process:
        print("No black screen - videos will play directly")
    
    return black_screen_process

def switch_to_random_video():
    """Switch to a random video"""
    global current_segment, black_screen_process
    
    # Stop black screen
    if black_screen_process:
        try:
            black_screen_process.terminate()
            black_screen_process.wait(timeout=1)
        except:
            black_screen_process.kill()
        black_screen_process = None
    
    # Select random video (avoid repeating same video)
    available_videos = VIDEO_SEGMENTS.copy()
    if current_segment:
        available_videos = [seg for seg in available_videos if seg["name"] != current_segment["name"]]
    
    if available_videos:
        selected_segment = random.choice(available_videos)
        print(f"Switching to: {selected_segment['name']}")
        
        # Play the selected segment
        play_video_segment(selected_segment['name'])
        
        # Set up timer to return to idle after video ends
        timer = threading.Timer(selected_segment['duration'], return_to_idle)
        timer.daemon = True
        timer.start()

def return_to_idle():
    """Return to idle state after video ends"""
    global current_video_process, current_segment
    
    print("Video finished")
    
    # Stop current video
    if current_video_process:
        try:
            current_video_process.terminate()
            current_video_process.wait(timeout=1)
        except:
            current_video_process.kill()
        current_video_process = None
    
    current_segment = None
    
    # Only show black screen if it's working
    if not black_screen_failed:
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
    """Play boot sound with better audio device detection"""
    if not os.path.exists(BOOT_SOUND_FILE):
        print(f"Boot sound file not found: {BOOT_SOUND_FILE}")
        return
    
    # Check file info
    try:
        result = subprocess.run(['file', BOOT_SOUND_FILE], capture_output=True, text=True)
        print(f"Boot sound file info: {result.stdout}")
    except:
        pass
    
    print("Playing boot sound")
    
    # Try multiple methods to play the sound
    audio_device = get_audio_device()
    
    # Method 1: Try with VLC
    try:
        env = os.environ.copy()
        env['DISPLAY'] = ':0'
        
        process = subprocess.Popen([
            "cvlc", "--play-and-exit", "--no-osd",
            "--aout=alsa", f"--alsa-audio-device={audio_device}",
            "--intf", "dummy",
            BOOT_SOUND_FILE
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        
        # Wait a bit and check if it's working
        time.sleep(1)
        if process.poll() is None:
            print("Boot sound playing with VLC")
            return
        else:
            stdout, stderr = process.communicate()
            print(f"VLC boot sound failed: {stderr.decode()}")
    except Exception as e:
        print(f"VLC boot sound error: {e}")
    
    # Method 2: Try with aplay as fallback
    try:
        print("Trying boot sound with aplay")
        subprocess.run(['aplay', BOOT_SOUND_FILE], check=True)
        print("Boot sound played with aplay")
    except Exception as e:
        print(f"aplay boot sound error: {e}")

def check_processes():
    """Check if processes are still running"""
    global current_video_process, current_segment
    
    # Check if video process finished
    if current_video_process and current_video_process.poll() is not None:
        print("Video process finished")
        current_video_process = None
        current_segment = None
        # Only restart black screen if it's not failing
        if not black_screen_failed:
            show_black_screen()

# === Main Loop ===
try:
    # Set display environment
    os.environ['DISPLAY'] = ':0'
    
    # Kill any existing VLC processes
    kill_all_vlc()
    
    # Play boot sound with better error handling
    play_boot_sound()
    time.sleep(3)  # Give more time for boot sound
    
    # Try to start with black screen
    show_black_screen()
    
    print("System ready. Press button to switch videos...")
    
    button_last_state = GPIO.HIGH
    last_button_time = 0
    debounce_delay = 0.3
    last_process_check = 0

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
        
        # Check process status (rate limited)
        if current_time - last_process_check > 1.0:
            check_processes()
            last_process_check = current_time
        
        time.sleep(0.05)

except KeyboardInterrupt:
    print("Exiting program...")

finally:
    cleanup_all()
    GPIO.cleanup()
    print("Cleanup complete!")
