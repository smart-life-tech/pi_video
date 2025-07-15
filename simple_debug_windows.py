import vlc
import time
import threading
import random
import os
import argparse

# === Configuration ===
VIDEO_FOLDER = "c:/Users/USER/Documents/raspberrypi/pi_video/"
MERGED_VIDEO = "c:/Users/USER/Documents/raspberrypi/pi_video/merged_videos.mp4"
BOOT_SOUND_FILE = "c:/Users/USER/Documents/raspberrypi/pi_video/boot_sound.wav"

# Video segments timing (in seconds)
VIDEO_SEGMENTS = [
    {"name": "video1", "start": 0, "duration": 45.9},
    {"name": "video2", "start": 45.9, "duration": 42.2},
    {"name": "video3", "start": 88.0, "duration": 22.9},
]

# Global variables
vlc_instance = None
vlc_player = None
current_video_playing = False

def debug_print(message):
    """Print debug messages with timestamp"""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] DEBUG: {message}")

def setup_vlc():
    """Setup VLC instance and player"""
    global vlc_instance, vlc_player
    
    debug_print("Setting up VLC...")
    
    try:
        # Create VLC instance
        vlc_instance = vlc.Instance([
            '--fullscreen',
            '--no-osd',
            '--no-video-title-show',
            '--loop',
            '--quiet'
        ])
        
        # Create media player
        vlc_player = vlc_instance.media_player_new()
        
        debug_print("✅ VLC instance created successfully")
        return True
        
    except Exception as e:
        debug_print(f"❌ Failed to create VLC instance: {e}")
        return False

def load_merged_video():
    """Load the merged video into VLC"""
    global vlc_player
    
    if not os.path.exists(MERGED_VIDEO):
        debug_print(f"❌ Merged video not found: {MERGED_VIDEO}")
        return False
    
    try:
        # Create media object
        media = vlc_instance.media_new(MERGED_VIDEO)
        
        # Set media to player
        vlc_player.set_media(media)
        
        debug_print(f"✅ Loaded video: {MERGED_VIDEO}")
        return True
        
    except Exception as e:
        debug_print(f"❌ Failed to load video: {e}")
        return False

def play_video_segment(segment_index):
    """Play a specific video segment using VLC"""
    global current_video_playing, vlc_player
    
    if vlc_player is None or segment_index >= len(VIDEO_SEGMENTS):
        debug_print(f"❌ Cannot play segment {segment_index}")
        return False
    
    segment = VIDEO_SEGMENTS[segment_index]
    start_time = segment["start"]
    duration = segment["duration"]
    
    debug_print(f"🎬 Playing {segment['name']} - Start: {start_time}s, Duration: {duration}s")
    current_video_playing = True
    
    def control_playback():
        try:
            # Stop if playing
            vlc_player.stop()
            time.sleep(0.2)
            
            # Set position (0.0 to 1.0)
            total_length = get_video_length()
            if total_length > 0:
                position = start_time / total_length
                vlc_player.set_position(position)
            
            # Start playing
            vlc_player.play()
            
            # Wait a bit for playback to start
            time.sleep(0.5)
            
            # Fine-tune position with time
            vlc_player.set_time(int(start_time * 1000))  # VLC uses milliseconds
            
            debug_print(f"▶️ Playing for {duration} seconds...")
            
            # Wait for the duration
            time.sleep(duration)
            
            # Pause the video
            vlc_player.pause()
            
            debug_print(f"⏸️ Finished playing {segment['name']}")
            
        except Exception as e:
            debug_print(f"❌ Playback error: {e}")
        
        finally:
            global current_video_playing
            current_video_playing = False
    
    # Run playback control in a separate thread
    playback_thread = threading.Thread(target=control_playback)
    playback_thread.daemon = True
    playback_thread.start()
    
    return True

def get_video_length():
    """Get total video length in seconds"""
    try:
        if vlc_player and vlc_player.get_media():
            # May need to play briefly to get length
            was_playing = vlc_player.is_playing()
            if not was_playing:
                vlc_player.play()
                time.sleep(0.5)
                vlc_player.pause()
            
            length_ms = vlc_player.get_length()
            return length_ms / 1000.0 if length_ms > 0 else 0
    except:
        pass
    return 0

def play_boot_sound():
    """Play boot sound using VLC"""
    if not os.path.exists(BOOT_SOUND_FILE):
        debug_print("❌ Boot sound file not found")
        return
    
    try:
        # Create separate VLC instance for audio
        audio_instance = vlc.Instance(['--no-video'])
        audio_player = audio_instance.media_player_new()
        
        # Load and play sound
        media = audio_instance.media_new(BOOT_SOUND_FILE)
        audio_player.set_media(media)
        audio_player.play()
        
        debug_print("🔊 Playing boot sound...")
        
        # Wait for sound to finish (estimate 3 seconds)
        time.sleep(3)
        
        audio_player.stop()
        debug_print("✅ Boot sound finished")
        
    except Exception as e:
        debug_print(f"❌ Boot sound error: {e}")

def test_vlc_setup():
    """Test VLC setup"""
    debug_print("=== TESTING VLC SETUP ===")
    
    if not setup_vlc():
        return False
    
    if not load_merged_video():
        return False
    
    # Test getting video info
    length = get_video_length()
    debug_print(f"Video length: {length:.1f} seconds ({length/60:.1f} minutes)")
    
    debug_print("✅ VLC setup successful")
    return True

def random_selection_test():
    """Test random video segment selection"""
    debug_print("=== RANDOM SELECTION TEST ===")
    
    if not test_vlc_setup():
        debug_print("❌ VLC setup failed")
        return
    
    # Randomly select a segment
    segment_index = random.randint(0, len(VIDEO_SEGMENTS) - 1)
    selected_segment = VIDEO_SEGMENTS[segment_index]
    
    debug_print(f"🎲 RANDOMLY SELECTED: {selected_segment['name']} (segment {segment_index + 1})")
    debug_print(f"   Start: {selected_segment['start']}s")
    debug_print(f"   Duration: {selected_segment['duration']}s")
    
    # Play the segment
    play_video_segment(segment_index)
    
    # Wait for playback to complete
    while current_video_playing:
        time.sleep(0.1)
    
    debug_print("✅ Random selection test completed")

def interactive_mode():
    """Interactive mode with VLC control"""
    debug_print("=== VLC INTERACTIVE MODE ===")
    
    if not test_vlc_setup():
        debug_print("❌ VLC setup failed")
        return
    
    debug_print("✅ VLC ready for interactive testing")
    debug_print("Commands:")
    debug_print("  1, 2, 3 - Play video segment")
    debug_print("  r - Random selection")
    debug_print("  b - Play boot sound")
    debug_print("  p - Pause/Resume")
    debug_print("  s - Stop")
    debug_print("  i - Video info")
    debug_print("  q - Quit")
    
    try:
        while True:
            command = input("\nEnter command: ").strip().lower()
            
            if command == 'q':
                break
            elif command in ['1', '2', '3']:
                segment_index = int(command) - 1
                if segment_index < len(VIDEO_SEGMENTS):
                    debug_print(f"Playing segment {command}")
                    play_video_segment(segment_index)
                else:
                    debug_print(f"Invalid segment: {command}")
            elif command == 'r':
                segment_index = random.randint(0, len(VIDEO_SEGMENTS) - 1)
                debug_print(f"Random selection: {VIDEO_SEGMENTS[segment_index]['name']}")
                play_video_segment(segment_index)
            elif command == 'b':
                play_boot_sound()
            elif command == 'p':
                if vlc_player:
                    vlc_player.pause()
                    debug_print("⏸️ Paused/Resumed")
            elif command == 's':
                if vlc_player:
                    vlc_player.stop()
                    debug_print("⏹️ Stopped")
            elif command == 'i':
                length = get_video_length()
                current_time = vlc_player.get_time() / 1000.0 if vlc_player else 0
                debug_print(f"Video length: {length:.1f}s, Current time: {current_time:.1f}s")
            else:
                debug_print(f"Unknown command: {command}")
                
    except KeyboardInterrupt:
        debug_print("Interrupted by user")
    
    finally:
        if vlc_player:
            vlc_player.stop()
        debug_print("VLC stopped")

def main():
    parser = argparse.ArgumentParser(description='VLC Pi Video Debug (Windows)')
    parser.add_argument('--test', '-t', action='store_true', help='Test VLC setup')
    parser.add_argument('--random', '-r', action='store_true', help='Random selection test')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    parser.add_argument('--segment', '-s', type=int, choices=[1, 2, 3], help='Play specific segment')
    parser.add_argument('--boot-sound', '-b', action='store_true', help='Test boot sound')
    
    args = parser.parse_args()
    
    if args.test:
        test_vlc_setup()
    elif args.random:
        random_selection_test()
    elif args.interactive:
        interactive_mode()
    elif args.segment:
        if test_vlc_setup():
            play_video_segment(args.segment - 1)
            while current_video_playing:
                time.sleep(0.1)
    elif args.boot_sound:
        play_boot_sound()
    else:
        # Default: interactive mode
        interactive_mode()

if __name__ == "__main__":
    main()
