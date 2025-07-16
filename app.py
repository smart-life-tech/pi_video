import RPi.GPIO as GPIO
import subprocess
import random
import time
import os
import threading
import signal

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
video_processes = {}
black_screen_process = None
current_active_video = None
system_running = True

def kill_all_vlc():
    """Kill all VLC processes"""
    try:
        subprocess.call(["pkill", "-f", "vlc"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.5)
    except:
        pass

def create_video_process(segment_name, segment_data):
    """Create a VLC process for a video segment, ready but not playing"""
    start_time = segment_data["start"]
    duration = segment_data["duration"]
    stop_time = start_time + duration
    
    print(f"Creating process for {segment_name}")
    
    # Create VLC process with proper environment
    env = os.environ.copy()
    env['DISPLAY'] = ':0'
    
    process = subprocess.Popen([
        "cvlc", 
        "--fullscreen", 
        "--no-osd",
        "--no-video-title-show",
        "--aout=alsa", 
        "--alsa-audio-device=hw:0,0",
        f"--start-time={start_time}",
        f"--stop-time={stop_time}",
        "--intf", "dummy",  # No interface dialogs
        "--extraintf", "hotkeys",  # Enable hotkeys
        MERGED_VIDEO
    ], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    
    return process

def create_black_screen_process():
    """Create black screen VLC process"""
    if not os.path.exists(BLACK_SCREEN_VIDEO):
        print("Black screen video not found")
        return None
    
    print("Creating black screen process")
    
    env = os.environ.copy()
    env['DISPLAY'] = ':0'
    
    process = subprocess.Popen([
        "cvlc", 
        "--fullscreen", 
        "--no-video-title-show", 
        "--no-osd",
        "--loop", 
        "--no-audio",
        "--intf", "dummy",
        "--extraintf", "hotkeys",
        BLACK_SCREEN_VIDEO
    ], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    
    return process

def pause_process(process):
    """Pause a VLC process"""
    if process and process.poll() is None:
        try:
            # Send pause signal (SIGSTOP)
            process.send_signal(signal.SIGSTOP)
            return True
        except:
            return False
    return False

def resume_process(process):
    """Resume a VLC process"""
    if process and process.poll() is None:
        try:
            # Send resume signal (SIGCONT)
            process.send_signal(signal.SIGCONT)
            return True
        except:
            return False
    return False

def initialize_all_processes():
    """Initialize all video processes"""
    global video_processes, black_screen_process
    
    print("Initializing all video processes...")
    
    # Kill any existing VLC processes
    kill_all_vlc()
    time.sleep(1)
    
    # Create video processes for each segment
    for segment in VIDEO_SEGMENTS:
        process = create_video_process(segment["name"], segment)
        if process:
            video_processes[segment["name"]] = process
            time.sleep(0.5)  # Stagger creation
            # Pause immediately after creation
            pause_process(process)
    
    # Create black screen process
    black_screen_process = create_black_screen_process()
    if black_screen_process:
        time.sleep(0.5)
    
    print("All processes initialized!")

def switch_to_random_video():
    """Switch to a random video smoothly"""
    global current_active_video, black_screen_process
    
    # Pause current video if any
    if current_active_video and current_active_video in video_processes:
        pause_process(video_processes[current_active_video])
    
    # Pause black screen
    if black_screen_process:
        pause_process(black_screen_process)
    
    # Select random video (avoid repeating same video)
    available_videos = list(video_processes.keys())
    if current_active_video in available_videos and len(available_videos) > 1:
        available_videos.remove(current_active_video)
    
    if available_videos:
        selected_video = random.choice(available_videos)
        print(f"Switching to: {selected_video}")
        
        # Resume the selected video
        if resume_process(video_processes[selected_video]):
            current_active_video = selected_video
            
            # Set up timer to return to black screen after video ends
            segment_duration = None
            for seg in VIDEO_SEGMENTS:
                if seg["name"] == selected_video:
                    segment_duration = seg["duration"]
                    break
            
            if segment_duration:
                timer = threading.Timer(segment_duration, return_to_black_screen)
                timer.daemon = True
                timer.start()

def return_to_black_screen():
    """Return to black screen after video ends"""
    global current_active_video, black_screen_process
    
    if current_active_video and current_active_video in video_processes:
        print(f"Video {current_active_video} finished, returning to black screen")
        pause_process(video_processes[current_active_video])
        current_active_video = None
    
    # Resume black screen
    if black_screen_process:
        resume_process(black_screen_process)

def cleanup_all_processes():
    """Clean up all processes"""
    global system_running, video_processes, black_screen_process
    
    print("Cleaning up all processes...")
    system_running = False
    
    # Terminate video processes
    for name, process in video_processes.items():
        if process:
            try:
                process.terminate()
                process.wait(timeout=2)
            except:
                process.kill()
    
    # Terminate black screen process
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

# === Main Loop ===
try:
    # Set display environment
    os.environ['DISPLAY'] = ':0'
    
    # Play boot sound
    play_boot_sound()
    time.sleep(2)
    
    # Initialize all processes
    initialize_all_processes()
    
    # Start with black screen
    if black_screen_process:
        resume_process(black_screen_process)
    
    print("System ready. Press button to switch videos...")
    
    button_last_state = GPIO.HIGH
    last_button_time = 0
    debounce_delay = 0.3

    while True:
        current_time = time.time()
        
        # Handle Shutdown Button
        if GPIO.input(SHUTDOWN_GPIO) == GPIO.LOW:
            print("Shutdown button pressed. Shutting down...")
            time.sleep(2)
            if GPIO.input(SHUTDOWN_GPIO) == GPIO.LOW:
                cleanup_all_processes()
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
        time.sleep(0.05)

except KeyboardInterrupt:
    print("Exiting program...")

finally:
    cleanup_all_processes()
    GPIO.cleanup()
    print("Cleanup complete!")
