import RPi.GPIO as GPIO
import subprocess
import random
import time
import os

# === Configuration ===
BUTTON_GPIO = 17  # Video trigger button
POWER_SWITCH_GPIO = 27  # On/Off switch
SHUTDOWN_GPIO = 22  # Shutdown button
VIDEO_FOLDER = "/home/pi-five/pi_video"  # Folder containing video files
VIDEO_FILES = [
    "video1.mp4",
    "video2.mp4",
    "video3.mp4"
]
BOOT_SOUND_FILE = "/home/pi-five/pi_video/boot_sound.mp3"  # Sound to play on boot

# === Setup ===
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(POWER_SWITCH_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(SHUTDOWN_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# === Utility Functions ===
def play_video(file_name):
    full_path = os.path.join(VIDEO_FOLDER, file_name)
    if not os.path.exists(full_path):
        print(f"Video file not found: {full_path}")
        return

    print(f"Playing: {full_path}")
    subprocess.call(["pkill", "-f", "vlc"])

    subprocess.Popen([
        "cvlc", "--fullscreen", "--no-osd", "--play-and-exit",
        "--aout=alsa", "--alsa-audio-device=hw:0,0",
        full_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def play_boot_sound():
    if os.path.exists(BOOT_SOUND_FILE):
        print("Playing boot sound")
        subprocess.Popen([
            "cvlc", "--play-and-exit", "--no-osd",
            "--aout=alsa", "--alsa-audio-device=hw:0,0",
            BOOT_SOUND_FILE
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print("Boot sound file not found")


test = True
test2 = True
# === Main Loop ===
try:
    play_boot_sound()
    print("System ready. Waiting for power switch ON...")
    while True:
        # Handle Shutdown Button
        if GPIO.input(SHUTDOWN_GPIO) == GPIO.LOW:
            print("Shutdown button pressed. Shutting down...")
            time.sleep(2)
            if GPIO.input(SHUTDOWN_GPIO) == GPIO.LOW:
                os.system("sudo shutdown -h now")

        # Handle Video Playback if System is ON
        if GPIO.input(POWER_SWITCH_GPIO) == GPIO.LOW or test2:  # Force ON for testing
            print("System is ON. Waiting for video button press...")
            test2 = False
            while GPIO.input(POWER_SWITCH_GPIO) == GPIO.HIGH:
                if GPIO.input(SHUTDOWN_GPIO) == GPIO.LOW:
                    print("Shutdown button pressed. Shutting down...")
                    time.sleep(2)
                    if GPIO.input(SHUTDOWN_GPIO) == GPIO.LOW:
                        os.system("sudo shutdown -h now")

                if GPIO.input(BUTTON_GPIO) == GPIO.LOW :  # Force ON for testing
                    print("Video trigger pressed")
                    selected_video = random.choice(VIDEO_FILES)
                    print(f"Selected video: {selected_video}")
                    test = False
                    play_video(selected_video)

                    while GPIO.input(BUTTON_GPIO) == GPIO.LOW:
                        time.sleep(0.1)
                    time.sleep(0.3)
                time.sleep(0.05)

            print("System turned OFF. Waiting...")
        time.sleep(0.2)

except KeyboardInterrupt:
    print("Exiting program...")

finally:
    GPIO.cleanup()
