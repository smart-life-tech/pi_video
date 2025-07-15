from moviepy  import VideoFileClip, concatenate_videoclips
import os

# === Configuration ===
VIDEO_FOLDER = "c:/Users/USER/Documents/raspberrypi/pi_video/"
VIDEO_FILES = [
    "video1.mp4",
    "video2.mp4", 
    "video3.mp4"
]
MERGED_VIDEO = "merged_videos.mp4"
TARGET_SIZE = (1920, 1080)  # Target resolution

def get_video_info(video_path):
    """Get video information using moviepy"""
    try:
        clip = VideoFileClip(video_path)
        info = {
            "duration": clip.duration,
            "resolution": f"{clip.w}x{clip.h}",
            "fps": clip.fps
        }
        clip.close()
        return info
    except Exception as e:
        print(f"Error getting info for {video_path}: {e}")
        return None

def resize_clip(clip, target_size):
    """Resize clip to target size with padding"""
    target_w, target_h = target_size
    
    # Calculate scaling to fit within target size
    scale_w = target_w / clip.w
    scale_h = target_h / clip.h
    scale = min(scale_w, scale_h)
    
    # Resize maintaining aspect ratio
    new_w = int(clip.w * scale)
    new_h = int(clip.h * scale)
    
    resized_clip = clip.resize((new_w, new_h))
    
    # Add padding if needed
    if new_w != target_w or new_h != target_h:
        from moviepy import ColorClip, CompositeVideoClip
        
        # Create black background
        background = ColorClip(size=target_size, color=(0, 0, 0), duration=clip.duration)
        
        # Center the resized clip
        x_offset = (target_w - new_w) // 2
        y_offset = (target_h - new_h) // 2
        
        final_clip = CompositeVideoClip([
            background,
            resized_clip.set_position((x_offset, y_offset))
        ])
        
        resized_clip.close()
        background.close()
        return final_clip
    
    return resized_clip

def merge_videos():
    """Merge videos using moviepy"""
    print("Merging videos using moviepy...")
    
    os.chdir(VIDEO_FOLDER)
    
    clips = []
    segments = []
    current_start = 0
    
    # Load and process each video
    for i, video_file in enumerate(VIDEO_FILES):
        if not os.path.exists(video_file):
            print(f"Missing: {video_file}")
            continue
        
        print(f"Processing {video_file}...")
        
        # Get original info
        info = get_video_info(video_file)
        if not info:
            continue
        
        print(f"  Original: {info['resolution']} - {info['duration']:.1f}s - {info['fps']:.1f}fps")
        
        # Load clip
        try:
            clip = VideoFileClip(video_file)
            
            # Resize to target resolution
            resized_clip = resize_clip(clip, TARGET_SIZE)
            clips.append(resized_clip)
            
            # Store timing info
            segment = {
                "name": f"video{i+1}",
                "start": round(current_start, 1),
                "duration": round(info["duration"], 1),
                "original_resolution": info["resolution"]
            }
            segments.append(segment)
            current_start += info["duration"]
            
            print(f"  Processed: {TARGET_SIZE[0]}x{TARGET_SIZE[1]} - {info['duration']:.1f}s")
            
            clip.close()
            
        except Exception as e:
            print(f"Error processing {video_file}: {e}")
            continue
    
    if not clips:
        print("❌ No valid clips to merge")
        return None
    
    # Concatenate all clips
    print(f"\nConcatenating {len(clips)} clips...")
    try:
        final_clip = concatenate_videoclips(clips, method="compose")
        
        # Write the merged video
        print(f"Writing merged video to {MERGED_VIDEO}...")
        final_clip.write_videofile(
            MERGED_VIDEO,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            fps=24  # Standard fps
        )
        
        # Clean up
        final_clip.close()
        for clip in clips:
            clip.close()
        
        print("✅ Merge completed successfully!")
        return segments
        
    except Exception as e:
        print(f"❌ Error during merge: {e}")
        return None

def verify_and_generate_code(segments):
    """Verify merged video and generate code"""
    merged_path = os.path.join(VIDEO_FOLDER, MERGED_VIDEO)
    
    if not os.path.exists(merged_path):
        print("❌ Merged video not found")
        return
    
    # Check merged video
    info = get_video_info(merged_path)
    if info:
        file_size = os.path.getsize(merged_path) / (1024*1024)
        print(f"\n✅ Merged video: {info['resolution']} - {info['duration']:.1f}s - {file_size:.1f}MB")
        
        if segments:
            print("\n" + "="*60)
            print("COPY THIS INTO YOUR app.py FILE:")
            print("="*60)
            
            print("VIDEO_SEGMENTS = [")
            for segment in segments:
                print(f'    {{"name": "{segment["name"]}", "start": {segment["start"]}, "duration": {segment["duration"]}}},')
            print("]")
            
            print(f"\n# All videos scaled to: {TARGET_SIZE[0]}x{TARGET_SIZE[1]}")
            print("# Original resolutions:")
            for segment in segments:
                print(f"# {segment['name']}: {segment['original_resolution']}")
            
            print("\n" + "="*60)
            
            # Save to file
            with open("video_timings.txt", "w") as f:
                f.write("VIDEO_SEGMENTS = [\n")
                for segment in segments:
                    f.write(f'    {{"name": "{segment["name"]}", "start": {segment["start"]}, "duration": {segment["duration"]}}},\n')
                f.write("]\n\n")
                f.write(f"# All videos scaled to: {TARGET_SIZE[0]}x{TARGET_SIZE[1]}\n")
                f.write("# Original resolutions:\n")
                for segment in segments:
                    f.write(f"# {segment['name']}: {segment['original_resolution']}\n")
            
            print("✅ Timings saved to video_timings.txt")
    else:
        print("❌ Could not verify merged video")

def main():
    print("MoviePy Video Merger")
    print("=" * 30)
    print(f"Target resolution: {TARGET_SIZE[0]}x{TARGET_SIZE[1]}")
    print("=" * 30)
    
    try:
        segments = merge_videos()
        if segments:
            verify_and_generate_code(segments)
        else:
            print("❌ Merge failed")
    except KeyboardInterrupt:
        print("\n❌ Merge interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()