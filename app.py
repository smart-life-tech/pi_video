import RPi.GPIO as GPIO
import subprocess
import random
import time
import os
import threading
import queue

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
video_threads = {}
black_screen_thread = None
current_active_video = None
system_running = True

class VideoThread:
    def __init__(self, segment_name, segment_data):
        self.segment_name = segment_name
        self.segment_data = segment_data
        self.process = None
        self.command_queue = queue.Queue()
        self.is_active = False
        self.is_ready = False
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
    
    def _run(self):
        """Main thread loop for this video segment"""
        global system_running
        
        while system_running:
            try:
                # Wait for commands with timeout
                try:
                    command = self.command_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                if command == "prepare":
                    self._prepare_video()
                elif command == "play":
                    self._play_video()
                elif command == "pause":
                    self._pause_video()
                elif command == "stop":
                    self._stop_video()
                elif command == "cleanup":
                    self._cleanup()
                    break
                    
            except Exception as e:
                print(f"Error in video thread {self.segment_name}: {e}")
    
    def _prepare_video(self):
        """Prepare video (load and pause at start position)"""
        if self.process:
            return
        
        start_time = self.segment_data["start"]
        duration = self.segment_data["duration"]
        stop_time = start_time + duration
        
        print(f"Preparing {self.segment_name} at {start_time}s")
        
        # Start VLC paused at the correct position
        self.process = subprocess.Popen([
            "cvlc", "--fullscreen", "--no-osd",
            "--aout=alsa", "--alsa-audio-device=hw:0,0",
            f"--start-time={start_time}",
            f"--stop-time={stop_time}",
            "--start-paused",  # Start in paused state
            MERGED_VIDEO
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        time.sleep(0.5)  # Give VLC time to load
        self.is_ready = True
    
    def _play_video(self):
        """Resume/play the video"""
        if self.process and self.is_ready:
            print(f"Playing {self.segment_name}")
            # Send play command via stdin (VLC hotkey)
            try:
                self.process.stdin.write(b' ')  # Space bar = play/pause
                self.process.stdin.flush()
            except:
                # Alternative: use xdotool to send space key to VLC window
                subprocess.call(["xdotool", "search", "--name", "VLC", "key", "space"], 
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.is_active = True
    
    def _pause_video(self):
        """Pause the video"""
        if self.process and self.is_active:
            print(f"Pausing {self.segment_name}")
            try:
                self.process.stdin.write(b' ')  # Space bar = play/pause
                self.process.stdin.flush()
            except:
                subprocess.call(["xdotool", "search", "--name", "VLC", "key", "space"], 
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.is_active = False
    
    def _stop_video(self):
        """Stop and hide the video"""
        if self.process:
            print(f"Stopping {self.segment_name}")
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except:
                self.process.kill()
            self.process = None
            self.is_active = False
            self.is_ready = False
    
    def _cleanup(self):
        """Clean up resources"""
        self._stop_video()
    
    def send_command(self, command):
        """Send command to this video thread"""
        self.command_queue.put(command)

class BlackScreenThread:
    def __init__(self):
        self.process = None
        self.command_queue = queue.Queue()
        self.is_active = False
        self.is_ready = False
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
    
    def _run(self):
        """Main thread loop for black screen"""
        global system_running
        
        while system_running:
            try:
                try:
                    command = self.command_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                if command == "prepare":
                    self._prepare_black_screen()
                elif command == "show":
                    self._show_black_screen()
                elif command == "hide":
                    self._hide_black_screen()
                elif command == "cleanup":
                    self._cleanup()
                    break
                    
            except Exception as e:
                print(f"Error in black screen thread: {e}")
    
    def _prepare_black_screen(self):
        """Prepare black screen video"""
        if self.process or not os.path.exists(BLACK_SCREEN_VIDEO):
            return
        
        print("Preparing black screen")
        self.process = subprocess.Popen([
            "cvlc", "--fullscreen", "--no-video-title-show", "--no-osd",
            "--loop", "--no-audio", "--start-paused",
            BLACK_SCREEN_VIDEO
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        time.sleep(0.5)
        self.is_ready = True
    
    def _show_black_screen(self):
        """Show black screen"""
        if self.process and self.is_ready and not self.is_active:
            print("Showing black screen")
            try:
                self.process.stdin.write(b' ')  # Play
                self.process.stdin.flush()
            except:
                subprocess.call(["xdotool", "search", "--name", "VLC", "key", "space"], 
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.is_active = True
    
    def _hide_black_screen(self):
        """Hide black screen"""
        if self.process and self.is_active:
            print("Hiding black screen")
            try:
                self.process.stdin.write(b' ')  # Pause
                self.process.stdin.flush()
            except:
                subprocess.call(["xdotool", "search", "--name", "VLC", "key", "space"], 
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.is_active = False
    
    def _cleanup(self):
        """Clean up resources"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except:
                self.process.kill()
            self.process = None
    
    def send_command(self, command):
        """Send command to black screen thread"""
        self.command_queue.put(command)

def initialize_all_threads():
    """Initialize all video threads and black screen thread"""
    global video_threads, black_screen_thread
    
    print("Initializing all video threads...")
    
    # Create video threads for each segment
    for segment in VIDEO_SEGMENTS:
        thread = VideoThread(segment["name"], segment)
        video_threads[segment["name"]] = thread
        # Prepare each video (load and pause)
        thread.send_command("prepare")
    
    # Create black screen thread
    black_screen_thread = BlackScreenThread()
    black_screen_thread.send_command("prepare")
    
    # Wait for all threads to be ready
    time.sleep(2)
    
    # Start with black screen
    black_screen_thread.send_command("show")
    
    print("All threads initialized and ready!")

def switch_to_random_video():
    """Switch to a random video smoothly"""
    global current_active_video
    
    # Hide current video if any
    if current_active_video:
        video_threads[current_active_video].send_command("pause")
    
    # Hide black screen
    if black_screen_thread:
        black_screen_thread.send_command("hide")
    
    # Select random video
    available_videos = list(video_threads.keys())
    if current_active_video in available_videos:
        available_videos.remove(current_active_video)  # Don't repeat same video
    
    if available_videos:
        selected_video = random.choice(available_videos)
        print(f"Switching to: {selected_video}")
        
        # Play the selected video
        video_threads[selected_video].send_command("play")
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
    global current_active_video
    
    if current_active_video:
        print(f"Video {current_active_video} finished, returning to black screen")
        video_threads[current_active_video].send_command("pause")
        current_active_video = None
    
    if black_screen_thread:
        black_screen_thread.send_command("show")

def cleanup_all_threads():
    """Clean up all threads"""
    global system_running
    
    print("Cleaning up all threads...")
    system_running = False
    
    # Clean up video threads
    for thread in video_threads.values():
        thread.send_command("cleanup")
    
    # Clean up black screen thread
    if black_screen_thread:
        black_screen_thread.send_command("cleanup")
    
    # Kill any remaining VLC processes
    time.sleep(1)
    subprocess.call(["pkill", "-f", "vlc"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def play_boot_sound():
    """Play boot sound"""
    if os.path.exists(BOOT_SOUND_FILE):
        print("Playing boot sound")
        subprocess.Popen([
            "cvlc", "--play-and-exit", "--no-osd",
            "--aout=alsa", "--alsa-audio-device=hw:1,0",
            BOOT_SOUND_FILE
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# === Main Loop ===
try:
    # Check if xdotool is available (for sending keys to VLC)
    try:
        subprocess.check_call(["which", "xdotool"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        print("Warning: xdotool not found. Installing...")
        os.system("sudo apt-get update && sudo apt-get install -y xdotool")
    
    # Play boot sound
    play_boot_sound()
    time.sleep(1)
    
    # Initialize all threads
    initialize_all_threads()
    
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
                cleanup_all_threads()
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
    cleanup_all_threads()
    GPIO.cleanup()
    print("Cleanup complete!")
    