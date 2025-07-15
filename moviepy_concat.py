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

def concatenate(video_clip_paths, output_path, method="compose"):
    """Concatenates several video files into one video file
    and save it to `output_path`. Note that extension (mp4, etc.) must be added to `output_path`
    `method` can be either 'compose' or 'reduce':
        `reduce`: Reduce the quality of the video to the lowest quality on the list of `video_clip_paths`.
        `compose`: type help(concatenate_videoclips) for the info"""
    # create VideoFileClip object for each video file
    clips = [VideoFileClip(c) for c in video_clip_paths]
    if method == "reduce":
        # calculate minimum width & height across all clips
        min_height = min([c.h for c in clips])
        min_width = min([c.w for c in clips])
        # resize the videos to the minimum
        clips = [c.resize(newsize=(min_width, min_height)) for c in clips]
        # concatenate the final video
        final_clip = concatenate_videoclips(clips)
    elif method == "compose":
        # concatenate the final video with the compose method provided by moviepy
        final_clip = concatenate_videoclips(clips, method="compose")
    # write the output video file
    final_clip.write_videofile(output_path)

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

def merge_videos():
    """Merge videos using the concatenate function"""
    print("Merging videos using concatenate function...")
    
    os.chdir(VIDEO_FOLDER)
    
    # Check all files exist and get info
    video_paths = []
    segments = []
    current_start = 0
    
    for i, video_file in enumerate(VIDEO_FILES):
        if not os.path.exists(video_file):
            print(f"Missing: {video_file}")
            continue
        
        info = get_video_info(video_file)
        if not info:
            continue
        
        print(f"Found: {video_file} - {info['resolution']} - {info['duration']:.1f}s - {info['fps']:.1f}fps")
        
        video_paths.append(video_file)
        
        # Store timing info
        segment = {
            "name": f"video{i+1}",
            "start": round(current_start, 1),
            "duration": round(info["duration"], 1),
            "original_resolution": info["resolution"]
        }
        segments.append(segment)
        current_start += info["duration"]
    
    if not video_paths:
        print("ERROR: No valid video files found")
        return None
    
    # Try both methods
    methods_to_try = ["compose", "reduce"]
    
    for method in methods_to_try:
        print(f"\nTrying method: {method}")
        try:
            concatenate(video_paths, MERGED_VIDEO, method=method)
            print(f"SUCCESS: Merge completed using '{method}' method!")
            return segments
        except Exception as e:
            print(f"ERROR: Method '{method}' failed: {e}")
            continue
    
    print("ERROR: All methods failed")
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
            
            print("\n# Original resolutions:")
            for segment in segments:
                print(f"# {segment['name']}: {segment['original_resolution']}")
            
            print("\n" + "="*60)
            
            # Save to file
            with open("video_timings.txt", "w") as f:
                f.write("VIDEO_SEGMENTS = [\n")
                for segment in segments:
                    f.write(f'    {{"name": "{segment["name"]}", "start": {segment["start"]}, "duration": {segment["duration"]}}},\n')
                f.write("]\n\n")
                f.write("# Original resolutions:\n")
                for segment in segments:
                    f.write(f"# {segment['name']}: {segment['original_resolution']}\n")
            
            print("SUCCESS: Timings saved to video_timings.txt")
    else:
        print("ERROR: Could not verify merged video")

def main():
    print("MoviePy Concatenate Video Merger")
    print("=" * 35)
    
    try:
        segments = merge_videos()
        if segments:
            verify_and_generate_code(segments)
        else:
            print("ERROR: Merge failed")
    except KeyboardInterrupt:
        print("\nERROR: Merge interrupted by user")
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()