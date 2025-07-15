import RPi.GPIO as GPIO
import subprocess
import random
import time
import os
import threading

# === Configuration ===
BUTTON_GPIO = 17  # Video trigger button
SHUTDOWN_GPIO = 27  # Shutdown button
VIDEO_FOLDER = "/home/pi-five/pi_video"
MERGED_VIDEO = "/home/pi-five/pi_video/merged_videos.mp4"  # Single merged video file
BOOT_SOUND_FILE = "/home/pi-five/pi_video/boot_sound.wav"

# Video segments timing (in seconds) - UPDATE THESE AFTER GETTING DURATIONS
VIDEO_SEGMENTS = [
    {"name": "video1", "start": 0, "duration": 45.9},
    {"name": "video2", "start": 45.9, "duration": 42.2},
    {"name": "video3", "start": 88.0, "duration": 22.9},
]

# === Setup ===
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(SHUTDOWN_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Global variables
vlc_process = None
current_video_playing = False

# === Utility Functions ===
def test_hdmi_audio():
    """Test which HDMI port has audio"""
    print("Testing HDMI audio ports...")
    
    try:
        result = subprocess.run(["speaker-test", "-c", "2", "-D", "hw:1,0", "-t", "sine", "-l", "1"], 
                              capture_output=True, timeout=3)
        if result.returncode == 0:
            print("HDMI audio working on hw:1,0")
            return "hw:0,0"
    except:
        pass
    
    try:
        result = subprocess.run(["speaker-test", "-c", "2", "-D", "hw:0,0", "-t", "sine", "-l", "1"], 
                              capture_output=True, timeout=3)
        if result.returncode == 0:
            print("HDMI audio working on hw:0,0")
            return "hw:1,0"
    except:
        pass
    
    print("No HDMI audio detected, using hw:0,0 as fallback")
    return "hw:0,0"

def start_merged_video_loop(audio_device):
    """Start the merged video with VLC RC interface - no desktop flashing!"""
    global vlc_process
    
    if not os.path.exists(MERGED_VIDEO):
        print(f"Merged video not found: {MERGED_VIDEO}")
        return None
    
    print("Starting merged video with RC interface")
    
    # Kill any existing VLC
    subprocess.run(["pkill", "-9", "-f", "vlc"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.2)
    
    # Start VLC with RC interface for remote control
    vlc_process = subprocess.Popen([
        "cvlc",
        "--fullscreen",
        "--no-osd",
        "--no-video-title-show",
        "--intf=rc",
        "--rc-host=localhost:4212",
        "--loop",
        "--start-paused",
        "--aout=alsa",
        f"--alsa-audio-device={audio_device}",
        "--volume=256",
        "--gain=2.0",
        MERGED_VIDEO
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    time.sleep(2)  # Give VLC time to start RC interface
    return vlc_process

def send_vlc_command(command):
    """Send command to VLC via RC interface"""
    try:
        process = subprocess.Popen(['echo', command], stdout=subprocess.PIPE)
        subprocess.run(['nc', '-w', '1', 'localhost', '4212'], 
                      stdin=process.stdout, 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL)
    except:
        print(f"Failed to send VLC command: {command}")

def play_video_segment(segment_index):
    """Play a specific segment of the merged video"""
    global current_video_playing
    
    if vlc_process is None or segment_index >= len(VIDEO_SEGMENTS):
        return
    
    segment = VIDEO_SEGMENTS[segment_index]
    start_time = segment["start"]
    duration = segment["duration"]
    
    print(f"Playing {segment['name']} - Start: {start_time}s, Duration: {duration}s")
    current_video_playing = True
    
    def control_playback():
        # Seek to start position
        send_vlc_command(f"seek {start_time}")
        time.sleep(0.1)
        
        # Start playing
        send_vlc_command("play")
        
        # Wait for the duration of the video segment
        time.sleep(duration)
        
        # Pause the video (back to black frame)
        send_vlc_command("pause")
        
        # Seek to a black frame or beginning for next time
        send_vlc_command("seek 0")
        
        global current_video_playing
        current_video_playing = False
        print(f"Finished playing {segment['name']}")
    
    # Run playback control in a separate thread
    playback_thread = threading.Thread(target=control_playback)
    playback_thread.daemon = True
    playback_thread.start()

def play_boot_sound(audio_device):
    if os.path.exists(BOOT_SOUND_FILE):
        print(f"Playing boot sound on {audio_device}")
        subprocess.run([
            "aplay", "-D", audio_device, BOOT_SOUND_FILE
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print("Boot sound file not found")

def setup_system():
    """Setup system for kiosk mode"""
    # Setup display
    os.system("setterm -cursor off")
    os.system("clear")
    
    # Force HDMI audio
    os.system("amixer cset numid=3 2 2>/dev/null")
    os.system("amixer -c 0 set 'IEC958' unmute 2>/dev/null")
    os.system("amixer -c 1 set 'IEC958' unmute 2>/dev/null")

def update_video_timings():
    """Helper function to calculate video segment timings"""
    #print("=== UPDATE THESE TIMINGS IN THE CODE ===")
    total_duration = 0
    
    for i, video_file in enumerate(["video1.mp4", "video2.mp4", "video3.mp4"]):
        file_path = os.path.join(VIDEO_FOLDER, video_file)
        if os.path.exists(file_path):
            try:
                result = subprocess.run([
                    "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", file_path
                ], capture_output=True, text=True)
                
                duration = float(result.stdout.strip())
                print(f'    {{"name": "video{i+1}", "start": {total_duration}, "duration": {duration:.1f}}},')
                total_duration += duration
            except:
                print(f"Could not get duration for {video_file}")
    
    print("=====================================")

# === Main Loop ===
try:
    print("Setting up system...")
    setup_system()
    
    # Show current video timings and how to update them
    update_video_timings()
    
    # Detect working HDMI audio device
    audio_device = test_hdmi_audio()
    
    play_boot_sound(audio_device)
    time.sleep(2)
    
    # Start the merged video loop (paused, showing first frame)
    vlc_process = start_merged_video_loop(audio_device)
    
    if vlc_process is None:
        print("Failed to start VLC. Exiting.")
        exit(1)
    
    print("System ready. Waiting for video button press...")
    video_playing = False

    while True:
        # Handle Shutdown Button
        if GPIO.input(SHUTDOWN_GPIO) == GPIO.LOW:
            print("Shutdown button pressed. Shutting down...")
            time.sleep(2)
            if GPIO.input(SHUTDOWN_GPIO) == GPIO.LOW:
                if vlc_process:
                    vlc_process.terminate()
                os.system("sudo shutdown -h now")

        # Handle Video Button
        if GPIO.input(BUTTON_GPIO) == GPIO.LOW and not current_video_playing:
            print("Video trigger pressed")
            
            # Randomly select a video segment
            segment_index = random.randint(0, len(VIDEO_SEGMENTS) - 1)
            selected_segment = VIDEO_SEGMENTS[segment_index]
            print(f"Selected: {selected_segment['name']}")
            
            # Play the selected video segment
            play_video_segment(segment_index)

            # Debounce button
            while GPIO.input(BUTTON_GPIO) == GPIO.LOW:
                time.sleep(0.1)
            time.sleep(0.3)

        time.sleep(0.1)

except KeyboardInterrupt:
    print("Exiting program...")

finally:
    if vlc_process:
        vlc_process.terminate()
    subprocess.run(["pkill", "-9", "-f", "vlc"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    GPIO.cleanup()
    os.system("setterm -cursor on")
    print("Cleaning up...")
