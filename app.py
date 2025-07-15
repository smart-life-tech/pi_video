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
def get_hdmi_audio_device():
    """Try both HDMI ports to find the active one"""
    # Try HDMI port 0 first (most common)
    return "hw:0,0"  # vc4hdmi0

def kill_all_players():
    """Kill all video players aggressively"""
    subprocess.run(["pkill", "-9", "-f", "vlc"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.05)

def play_video(file_name):
    full_path = os.path.join(VIDEO_FOLDER, file_name)
    if not os.path.exists(full_path):
        print(f"Video file not found: {full_path}")
        return

    print(f"Playing: {full_path}")
    
    # Try HDMI port 0 first, then port 1 if needed
    hdmi_devices = ["hw:0,0", "hw:1,0"]
    
    for device in hdmi_devices:
        try:
            subprocess.run([
                "cvlc", 
                "--fullscreen", 
                "--play-and-exit",
                "--no-osd", 
                "--no-video-title-show", 
                "--no-mouse-events", 
                "--no-keyboard-events",
                "--intf=dummy",
                "--no-video-deco",
                "--no-embedded-video",
                "--no-qt-privacy-ask",
                "--no-qt-system-tray",
                "--aout=alsa",
                f"--alsa-audio-device={device}",
                "--volume=512",  # Max volume
                "--gain=3.0",    # High gain
                full_path
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            print(f"Audio played on {device}")
            break
        except:
            print(f"Failed to play audio on {device}, trying next...")
            continue

def play_boot_sound():
    if os.path.exists(BOOT_SOUND_FILE):
        print("Playing boot sound")
        hdmi_devices = ["hw:0,0", "hw:1,0"]
        
        for device in hdmi_devices:
            try:
                subprocess.Popen([
                    "cvlc", "--play-and-exit", "--no-osd", "--intf=dummy",
                    "--aout=alsa", f"--alsa-audio-device={device}",
                    "--volume=512", "--gain=3.0",
                    BOOT_SOUND_FILE
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"Boot sound using {device}")
                break
            except:
                continue
    else:
        print("Boot sound file not found")

def show_black_screen_loop():
    if os.path.exists(BLACK_SCREEN_VIDEO):
        print("Starting black screen loop")
        return subprocess.Popen([
            "cvlc", 
            "--fullscreen", 
            "--loop", 
            "--no-osd",
            "--no-video-title-show", 
            "--no-mouse-events", 
            "--no-keyboard-events",
            "--intf=dummy",
            "--no-video-deco",
            "--no-embedded-video",
            "--no-qt-privacy-ask",
            "--no-qt-system-tray",
            "--no-audio",
            BLACK_SCREEN_VIDEO
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print("Black screen video not found")
        return None

def setup_display():
    """Setup display to minimize flashing"""
    os.system("setterm -cursor off")
    os.system("clear")
    os.system("dmesg -n 1")

# === Main Loop ===
try:
    setup_display()
    
    # Setup audio for both HDMI ports
    os.system("amixer -c 0 set 'IEC958' unmute 2>/dev/null")
    os.system("amixer -c 1 set 'IEC958' unmute 2>/dev/null")
    os.system("amixer cset numid=3 2 2>/dev/null")  # Force HDMI
    
    print("HDMI Audio devices found:")
    print("- hw:0,0 (vc4hdmi0)")
    print("- hw:1,0 (vc4hdmi1)")
    
    play_boot_sound()
    time.sleep(2)  # Give boot sound time to play
    
    black_process = show_black_screen_loop()
    print("System ready. Waiting for video button press...")
    video_playing = False

    while True:
        # Handle Shutdown Button
        if GPIO.input(SHUTDOWN_GPIO) == GPIO.LOW:
            print("Shutdown button pressed. Shutting down...")
            time.sleep(2)
            if GPIO.input(SHUTDOWN_GPIO) == GPIO.LOW:
                kill_all_players()
                os.system("sudo shutdown -h now")

        # Handle Video Button
        if GPIO.input(BUTTON_GPIO) == GPIO.LOW and not video_playing:
            print("Video trigger pressed")
            video_playing = True

            selected_video = random.choice(VIDEO_FILES)
            print(f"Selected video: {selected_video}")
            
            # Kill black screen
            if black_process:
                black_process.terminate()
                black_process.wait()
            
            # Play video
            play_video(selected_video)

            # Restart black screen
            black_process = show_black_screen_loop()
            video_playing = False

            # Debounce button
            while GPIO.input(BUTTON_GPIO) == GPIO.LOW:
                time.sleep(0.1)
            time.sleep(0.3)

        time.sleep(0.1)

except KeyboardInterrupt:
    print("Exiting program...")

finally:
    kill_all_players()
    GPIO.cleanup()
    os.system("setterm -cursor on")
    print("Cleaning up...")
