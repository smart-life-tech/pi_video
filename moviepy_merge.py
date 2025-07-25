from moviepy import VideoFileClip, concatenate_videoclips
import os

# === Configuration ===
VIDEO_FOLDER = "c:/Users/USER/Documents/raspberrypi/pi_video/"
VIDEO_FILES = [
    "video1.mp4",
    "video2.mp4", 
    "video3.mp4"
]
MERGED_VIDEO = "merged_videos.mp4"

def get_video_info(video_path):
    """Get video information using moviepy"""
    try:
        clip = VideoFileClip(video_path)
        info = {
            "duration": clip.duration,
            "resolution": f"{clip.w}x{clip.h}",
            "fps": clip.fps,
            "width": clip.w,
            "height": clip.h
        }
        clip.close()
        return info
    except Exception as e:
        print(f"Error getting info for {video_path}: {e}")
        return None

def merge_videos():
    """Simple merge without any modifications"""
    print("Simple video merge (no modifications)...")
    
    os.chdir(VIDEO_FOLDER)
    
    clips = []
    segments = []
    current_start = 0
    
    # Load each video
    for i, video_file in enumerate(VIDEO_FILES):
        if not os.path.exists(video_file):
            print(f"Missing: {video_file}")
            continue
        
        print(f"Loading {video_file}...")
        
        # Get original info
        info = get_video_info(video_file)
        if not info:
            continue
        
        print(f"  {info['resolution']} - {info['duration']:.1f}s - {info['fps']:.1f}fps")
        
        # Load clip without any modifications
        try:
            clip = VideoFileClip(video_file)
            clips.append(clip)
            
            # Store timing info
            segment = {
                "name": f"video{i+1}",
                "start": round(current_start, 1),
                "duration": round(info["duration"], 1),
                "original_resolution": info["resolution"]
            }
            segments.append(segment)
            current_start += info["duration"]
            
            print(f"  Added to merge queue")
            
        except Exception as e:
            print(f"Error loading {video_file}: {e}")
            continue
    
    if not clips:
        print("ERROR: No valid clips to merge")
        return None
    
    # Simple concatenation
    print(f"\nConcatenating {len(clips)} clips...")
    try:
        # Use the simplest concatenation method
        final_clip = concatenate_videoclips(clips)
        
        # Write with minimal settings
        print(f"Writing merged video to {MERGED_VIDEO}...")
        final_clip.write_videofile(MERGED_VIDEO)
        
        # Clean up
        final_clip.close()
        for clip in clips:
            clip.close()
        
        print("SUCCESS: Basic merge completed!")
        return segments
        
    except Exception as e:
        print(f"ERROR: Error during merge: {e}")
        import traceback
        traceback.print_exc()
        return None

def verify_and_generate_code(segments):
    """Verify merged video and generate code"""
    merged_path = os.path.join(VIDEO_FOLDER, MERGED_VIDEO)
    
    if not os.path.exists(merged_path):
        print("ERROR: Merged video not found")
        return
    
    # Check merged video
    info = get_video_info(merged_path)
    if info:
        file_size = os.path.getsize(merged_path) / (1024*1024)
        print(f"\nSUCCESS: Merged video: {info['resolution']} - {info['duration']:.1f}s - {file_size:.1f}MB")
        
        if segments:
            print("\n" + "="*60)
            print("COPY THIS INTO YOUR app.py FILE:")
            print("="*60)
            
            print("VIDEO_SEGMENTS = [")
            for segment in segments:
                print(f'    {{"name": "{segment["name"]}", "start": {segment["start"]}, "duration": {segment["duration"]}}},')
            print("]")
            
            print("\n# Videos merged as-is (original specs):")
            for segment in segments:
                print(f"# {segment['name']}: {segment['original_resolution']}")
            
            print("\n" + "="*60)
            
            # Save to file
            with open("video_timings.txt", "w") as f:
                f.write("VIDEO_SEGMENTS = [\n")
                for segment in segments:
                    f.write(f'    {{"name": "{segment["name"]}", "start": {segment["start"]}, "duration": {segment["duration"]}}},\n')
                f.write("]\n\n")
                f.write("# Videos merged as-is (original specs):\n")
                for segment in segments:
                    f.write(f"# {segment['name']}: {segment['original_resolution']}\n")
            
            print("SUCCESS: Timings saved to video_timings.txt")
    else:
        print("ERROR: Could not verify merged video")

def main():
    print("Simple MoviePy Video Merger")
    print("=" * 30)
    print("Note: Videos will be merged as-is")
    print("=" * 30)
    
    try:
        segments = merge_videos()
        if segments:
            verify_and_generate_code(segments)
            print("\nIMPORTANT:")
            print("- If playback issues occur, use simple_merge.py with ffmpeg instead")
            print("- Or use the merge_and_extract.py script for proper scaling")
        else:
            print("ERROR: Merge failed")
    except KeyboardInterrupt:
        print("\nERROR: Merge interrupted by user")
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")

if __name__ == "__main__":
    main()
