# Pi Video Player

A Raspberry Pi-based video player system with hardware button controls for interactive video playback.

## Overview

This project creates a standalone video player system using a Raspberry Pi with physical button controls. The system can play random videos from a collection, has power control, and includes a shutdown mechanism - perfect for interactive displays, kiosks, or entertainment systems.

## Features

- **Random Video Playback**: Plays random videos from a predefined collection
- **Hardware Controls**: Physical buttons for power, video trigger, and shutdown
- **Boot Sound**: Plays a sound file on system startup
- **Safe Shutdown**: Proper shutdown button to prevent SD card corruption
- **Fullscreen Display**: Videos play in fullscreen mode with aspect ratio filling
- **Auto-restart**: Continuous operation until manually powered off

## Hardware Requirements

- Raspberry Pi (any model with GPIO pins)
- 3 Push buttons
- Breadboard and jumper wires
- Pull-up resistors (optional - using internal pull-ups)
- Display/Monitor with HDMI connection
- Speakers or audio output device

## GPIO Pin Configuration

| Component | GPIO Pin | Physical Pin |
|-----------|----------|--------------|
| Video Trigger Button | GPIO 17 | Pin 11 |
| Power Switch | GPIO 27 | Pin 13 |
| Shutdown Button | GPIO 22 | Pin 15 |

## Wiring Diagram

```
Button → GPIO Pin → Ground
├── Video Trigger → GPIO 17 → GND
├── Power Switch → GPIO 27 → GND
└── Shutdown Button → GPIO 22 → GND
```

All buttons are configured with internal pull-up resistors, so they trigger when pressed (LOW state).

## Software Requirements

- Raspberry Pi OS
- Python 3.x
- RPi.GPIO library
- omxplayer (for video playback)

## Installation

1. **Clone or download the project files to your Raspberry Pi**

2. **Install required dependencies:**
```bash
sudo apt update
sudo apt install python3-rpi.gpio omxplayer
```

3. **Create the required directories:**
```bash
mkdir -p /home/pi/Videos
```

4. **Add your video files to the Videos directory:**
   - Place your MP4 video files in `/home/pi/Videos/`
   - Update the `VIDEO_FILES` list in `app.py` with your actual video filenames

5. **Add boot sound (optional):**
   - Place your boot sound file at `/home/pi/boot_sound.mp3`

## Configuration

Edit the configuration section in `app.py` to customize:

```python
# GPIO pin assignments
BUTTON_GPIO = 17          # Video trigger button
POWER_SWITCH_GPIO = 27    # On/Off switch
SHUTDOWN_GPIO = 22        # Shutdown button

# File paths
VIDEO_FOLDER = "/home/pi/Videos"
VIDEO_FILES = [
    "video1.mp4",
    "video2.mp4",
    "video3.mp4"
]
BOOT_SOUND_FILE = "/home/pi/boot_sound.mp3"
```

## Usage

1. **Run the application:**
```bash
python3 app.py
```

2. **Operation:**
   - **Power On**: Press and hold the power switch
   - **Play Video**: While powered on, press the video trigger button to play a random video
   - **Shutdown**: Press and hold the shutdown button for 2 seconds to safely shutdown the Pi

## Auto-Start on Boot (Optional)

To automatically start the video player on boot:

1. **Create a systemd service:**
```bash
sudo nano /etc/systemd/system/pi-video.service
```

2. **Add the following content:**
```ini
[Unit]
Description=Pi Video Player
After=multi-user.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/pi_video
ExecStart=/usr/bin/python3 /home/pi/pi_video/app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

3. **Enable the service:**
```bash
sudo systemctl enable pi-video.service
sudo systemctl start pi-video.service
```

## File Structure

```
pi_video/
├── app.py              # Main application
├── README.md           # This file
└── /home/pi/Videos/    # Video files directory
    ├── video1.mp4
    ├── video2.mp4
    └── video3.mp4
```

## Troubleshooting

### Common Issues

1. **Videos not playing:**
   - Check if video files exist in `/home/pi/Videos/`
   - Verify video file names match those in `VIDEO_FILES` list
   - Ensure omxplayer is installed: `sudo apt install omxplayer`

2. **Buttons not responding:**
   - Check GPIO connections
   - Verify button wiring (should connect GPIO pin to ground when pressed)
   - Test with a multimeter or LED

3. **No audio:**
   - Check audio output settings: `sudo raspi-config` → Advanced Options → Audio
   - For HDMI audio: `sudo amixer cset numid=3 2`
   - For 3.5mm jack: `sudo amixer cset numid=3 1`

4. **Permission errors:**
   - Ensure the script has proper permissions: `chmod +x app.py`
   - Run with appropriate privileges if needed

### Debug Mode

Add debug prints by uncommenting or adding print statements throughout the code to monitor button states and system behavior.

## Customization Ideas

- Add LED indicators for system status
- Implement volume control buttons
- Add support for different video formats
- Create a web interface for remote control
- Add playlist management
- Implement video scheduling

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

This project is open source. Please check the repository for license details.

## Support

For issues and questions, please create an issue in the GitHub repository or contact the project maintainer.