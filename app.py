import RPi.GPIO as GPIO
import subprocess
import random
import time
import os
import threading
import ast  # For safely evaluating the VIDEO_SEGMENTS from file

# === Configuration ===
BUTTON_GPIO = 17  # Video trigger button
SHUTDOWN_GPIO = 27  # Shutdown button
VIDEO_FOLDER = "/home/pi-five/pi_video"  # Folder containing video files
MERGED_VIDEO = "/home/pi-five/pi_video/merged_videos.mp4"  # Single merged video
BOOT_SOUND_FILE = "/home/pi-five/pi_video/boot_sound.wav"  # Sound to play on boot
BLACK_SCREEN_VIDEO = "/home/pi-five/pi_video/black.mp4"  # Black screen video file
VIDEO_TIMINGS_FILE = "/home/pi-five/pi_video/video_timings.txt"  # Video timings file

# Video segments from video_timings.txt
# VIDEO_SEGMENTS = [
#     {"name": "video1", "start": 0, "duration": 45.9},
#     {"name": "video2", "start": 45.9, "duration": 42.2},
#     {"name": "video3", "start": 88.0, "duration": 22.9},
# ]

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
video_playing = False  # Track if video is currently playing
current_timer = None  # Track the current timer

def load_video_segments():
    """Load video segments from video_timings.txt file"""
    try:
        if not os.path.exists(VIDEO_TIMINGS_FILE):
            print(f"Video timings file not found: {VIDEO_TIMINGS_FILE}")
            # Fallback to default segments
            return [
                {"name": "video1", "start": 0, "duration": 45.9},
                {"name": "video2", "start": 45.9, "duration": 42.2},
                {"name": "video3", "start": 88.0, "duration": 22.9},
            ]
        
        with open(VIDEO_TIMINGS_FILE, 'r') as file:
            content = file.read()
            
        # Find the VIDEO_SEGMENTS line and extract the data
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('VIDEO_SEGMENTS = ['):
                # Extract the list part
                start_idx = line.find('[')
                if start_idx != -1:
                    # Read the complete list (might span multiple lines)
                    list_content = content[content.find('['):content.find(']') + 1]
                    # Safely evaluate the list
                    segments = ast.literal_eval(list_content)
                    print(f"Loaded {len(segments)} video segments from {VIDEO_TIMINGS_FILE}")
                    return segments
        
        print("VIDEO_SEGMENTS not found in file, using defaults")
        return [
            {"name": "video1", "start": 0, "duration": 45.9},
            {"name": "video2", "start": 45.9, "duration": 42.2},
            {"name": "video3", "start": 88.0, "duration": 22.9},
        ]
        
    except Exception as e:
        print(f"Error loading video segments: {e}")
        # Fallback to default segments
        return [
            {"name": "video1", "start": 0, "duration": 45.9},
            {"name": "video2", "start": 45.9, "duration": 42.2},
            {"name": "video3", "start": 88.0, "duration": 22.9},
        ]
# Load video segments from file
VIDEO_SEGMENTS = load_video_segments()
print(VIDEO_SEGMENTS)
def get_audio_device():
    """Detect the correct audio device"""
    try:
        result = subprocess.run(['aplay', '-l'], capture_output=True, text=True)
        output = result.stdout
        if 'HDMI' in output:
            return "hw:1,0"
        else:
            return "hw:0,0"
    except:
        return "hw:0,0"

def kill_all_vlc():
    """Kill all VLC processes"""
    try:
        subprocess.call(["pkill", "-f", "vlc"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.5)
    except:
        pass
def cancel_current_timer():
    """Cancel the current timer if it exists"""
    global current_timer
    if current_timer:
        current_timer.cancel()
        current_timer = None

def play_video_segment(segment_name):
    """Play a specific segment from the merged video"""
    global current_video_process, current_segment, video_playing
    # Prevent starting if already playing
    if video_playing:
        return None
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
    # if current_video_process:
    #     try:
    #         current_video_process.terminate()
    #         current_video_process.wait(timeout=1)
    #     except:
    #         current_video_process.kill()
    
    # Start new video process with no interface elements
    env = os.environ.copy()
    env['DISPLAY'] = ':0'
    
    audio_device = get_audio_device()
    
    current_video_process = subprocess.Popen([
        "cvlc", 
        "--fullscreen", 
        "--no-osd", 
        "--play-and-exit",
        "--no-video-title-show",
        "--no-snapshot-preview",
        "--no-spu",  # No subtitles
        "--no-disable-screensaver",
        #"--aout=alsa", 
        #f"--alsa-audio-device={audio_device}",
        f"--start-time={start_time}",
        f"--stop-time={stop_time}",
        "--intf", "dummy",  # No interface
        "--extraintf", "",  # No extra interfaces
        "--no-interact",  # No interaction
        #"--no-keyboard",  # No keyboard shortcuts
        "--no-mouse-events",  # No mouse events
        MERGED_VIDEO
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env, 
       stdin=subprocess.DEVNULL)  # Close stdin to prevent input
    
    video_playing = True
    return current_video_process

def show_black_screen():
    """Show black screen with no interface elements"""
    global black_screen_process, black_screen_failed, last_black_screen_attempt
    
    # Prevent rapid restart attempts
    current_time = time.time()
    if current_time - last_black_screen_attempt < 5:
        return black_screen_process
    
    last_black_screen_attempt = current_time
    
    # Kill any existing black screen process
    # if black_screen_process:
    #     try:
    #         black_screen_process.terminate()
    #         black_screen_process.wait(timeout=1)
    #     except:
    #         black_screen_process.kill()
    #     black_screen_process = None
    
    if not os.path.exists(BLACK_SCREEN_VIDEO):
        print(f"Black screen video not found: {BLACK_SCREEN_VIDEO}")
        black_screen_failed = True
        return None
    
    if not black_screen_failed:
        print("Starting black screen")
        
        env = os.environ.copy()
        env['DISPLAY'] = ':0'
        
        black_screen_process = subprocess.Popen([
            "cvlc", 
            "--fullscreen", 
            "--no-video-title-show", 
            "--no-osd",
            "--no-snapshot-preview",
            "--no-spu",
            "--no-disable-screensaver",
            "--loop", 
            "--no-audio",
            "--intf", "dummy",
            "--extraintf", "",
            "--no-interact",
            "--no-keyboard",
            "--no-mouse-events",
            BLACK_SCREEN_VIDEO
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env,
           stdin=subprocess.DEVNULL)
        
        # Check if it started successfully
        time.sleep(1)
        if black_screen_process.poll() is not None:
            print("Black screen failed")
            black_screen_failed = True
            black_screen_process = None
    
    return black_screen_process

def switch_to_random_video():
    """Switch to a random video - only if no video is currently playing"""
    global current_segment, black_screen_process, video_playing, current_timer
    
    # Don't switch if a video is already playing
    if video_playing or current_timer is not None:
        print("Video already playing, ignoring button press")
        return
    
    # Stop black screen
    # if black_screen_process:
    #     try:
    #         black_screen_process.terminate()
    #         black_screen_process.wait(timeout=1)
    #     except:
    #         black_screen_process.kill()
    #     black_screen_process = None
    
    # Cancel any existing timer (double check)
    cancel_current_timer()
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
        # timer = threading.Timer(selected_segment['duration'], return_to_idle)
        # timer.daemon = True
        # timer.start()
        current_timer = threading.Timer(selected_segment['duration'], return_to_idle)
        current_timer.daemon = True
        current_timer.start()

def return_to_idle():
    """Return to idle state after video ends"""
    global current_video_process, current_segment, video_playing,current_timer
    # Clear the timer reference since it's completed
    current_timer = None
    
    # Only proceed if we're actually playing a video
    if not video_playing or not system_running:
        return
    print("Video finished")
    
    # # Stop current video
    # if current_video_process:
    #     try:
    #         current_video_process.terminate()
    #         current_video_process.wait(timeout=1)
    #     except:
    #         current_video_process.kill()
    #     current_video_process = None
    
    current_segment = None
    video_playing = False
    
    # Only show black screen if it's working
    if not black_screen_failed:
        show_black_screen()

def cleanup_all():
    """Clean up all processes"""
    global system_running, current_video_process, black_screen_process
    
    print("Cleaning up all processes...")
    system_running = False
     # Cancel any running timer
    cancel_current_timer()
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
    """Play boot sound with aplay (more reliable)"""
    if not os.path.exists(BOOT_SOUND_FILE):
        print(f"Boot sound file not found: {BOOT_SOUND_FILE}")
        return
    
    print("Playing boot sound")
    
    try:
        subprocess.run(['aplay', BOOT_SOUND_FILE], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL, 
                      check=True)
        print("Boot sound played successfully")
    except Exception as e:
        print(f"Boot sound error: {e}")

def check_processes():
    """Check if processes are still running"""
    global current_video_process, current_segment, video_playing
    
    # Check if video process finished
    if current_video_process and current_video_process.poll() is not None:
        print("Video process finished")
        current_video_process = None
        current_segment = None
        video_playing = False
        # Cancel the timer since the video finished early
        cancel_current_timer()
        time.sleep(0.1)
        # Only restart black screen if it's not failing
        if not black_screen_failed and not video_playing:
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
    
    # Try to start with black screen
    show_black_screen()
    
    print("System ready. Press button to switch videos...")
    
    button_last_state = GPIO.HIGH
    last_button_time = 0
    debounce_delay = 2  # Increased debounce delay
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

        # Handle Video Button with debouncing - only when no video is playing
        button_current_state = GPIO.input(BUTTON_GPIO)
        
        if (button_current_state == GPIO.LOW and 
            button_last_state == GPIO.HIGH and 
            current_time - last_button_time > debounce_delay and
            not video_playing):  # Only allow when no video is playing
            
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
