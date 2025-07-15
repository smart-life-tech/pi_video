import subprocess
import os
import json

# === Configuration ===
VIDEO_FOLDER = "/home/pi-five/pi_video"
VIDEO_FILES = [
    "video1.mp4",
    "video2.mp4", 
    "video3.mp4"
]
MERGED_VIDEO = "merged_videos.mp4"
TARGET_WIDTH = 1920
TARGET_HEIGHT = 1080

def get_video_info(video_path):
    """Get video information including duration and resolution"""
    try:
        # Get duration
        duration_result = subprocess.run([
            "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", video_path
        ], capture_output=True, text=True, check=True)
        
        # Get resolution
        resolution_result = subprocess.run([
            "ffprobe", "-v", "quiet", "-select_streams", "v:0", 
            "-show_entries", "stream=width,height",
            "-of", "csv=s=x:p=0", video_path
        ], capture_output=True, text=True, check=True)
        
        duration = float(duration_result.stdout.strip())
        resolution = resolution_result.stdout.strip()
        
        return {
            "duration": duration,
            "resolution": resolution
        }
    except Exception as e:
        print(f"Error getting info for {video_path}: {e}")
        return None

def merge_videos():
    """Merge all videos into one file with consistent resolution"""
    print("Merging videos with resolution scaling...")
    
    # Change to video directory
    os.chdir(VIDEO_FOLDER)
    
    # Check if all video files exist and get their info
    video_info = []
    for video_file in VIDEO_FILES:
        if not os.path.exists(video_file):
            print(f"Missing video file: {video_file}")
            return False
        
        info = get_video_info(video_file)
        if info is None:
            return False
        
        video_info.append({
            "file": video_file,
            "duration": info["duration"],
            "resolution": info["resolution"]
        })
        
        print(f"{video_file}: {info['resolution']} - {info['duration']:.1f}s")
    
    # Build ffmpeg command with scaling
    input_args = []
    for video_file in VIDEO_FILES:
        input_args.extend(["-i", video_file])
    
    # Create filter complex with proper scaling and padding
    filter_parts = []
    
    # Scale and pad each video to target resolution
    for i in range(len(VIDEO_FILES)):
        filter_parts.append(
            f"[{i}:v]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={TARGET_WIDTH}:{TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,setsar=1[v{i}]"
        )
    
    # Concatenate scaled videos
    concat_inputs = ""
    for i in range(len(VIDEO_FILES)):
        concat_inputs += f"[v{i}][{i}:a]"
    
    filter_complex = ";".join(filter_parts) + f";{concat_inputs}concat=n={len(VIDEO_FILES)}:v=1:a=1[outv][outa]"
    
    # Full ffmpeg command
    ffmpeg_cmd = [
        "ffmpeg", "-y"  # -y to overwrite existing file
    ] + input_args + [
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-c:a", "aac",
        "-preset", "medium",
        "-crf", "23",
        MERGED_VIDEO
    ]
    
    try:
        print(f"Scaling all videos to {TARGET_WIDTH}x{TARGET_HEIGHT} and merging...")
        print("This may take a few minutes...")
        
        # Print the command for debugging
        print("FFmpeg command:")
        print(" ".join(ffmpeg_cmd))
        
        result = subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
        print(f"Successfully merged videos into {MERGED_VIDEO}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error merging videos: {e}")
        if e.stderr:
            print(f"FFmpeg stderr: {e.stderr}")
        return False

def extract_timings():
    """Extract timing information for each video segment"""
    print("\nExtracting video timings...")
    
    segments = []
    current_start = 0
    
    for i, video_file in enumerate(VIDEO_FILES):
        video_path = os.path.join(VIDEO_FOLDER, video_file)
        info = get_video_info(video_path)
        
        if info and info["duration"] > 0:
            segment = {
                "name": f"video{i+1}",
                "start": round(current_start, 1),
                "duration": round(info["duration"], 1),
                "end": round(current_start + info["duration"], 1),
                "original_resolution": info["resolution"]
            }
            segments.append(segment)
            current_start += info["duration"]
            
            print(f"{video_file}: {info['resolution']} -> {TARGET_WIDTH}x{TARGET_HEIGHT}, Duration = {info['duration']:.1f}s")
        else:
            print(f"Could not get info for {video_file}")
    
    return segments

def generate_updated_code(segments):
    """Generate the updated Python code with correct timings"""
    print("\n" + "="*60)
    print("COPY THIS INTO YOUR app.py FILE:")
    print("="*60)
    
    print("# Updated VIDEO_SEGMENTS with correct timings:")
    print("VIDEO_SEGMENTS = [")
    for segment in segments:
        print(f'    {{"name": "{segment["name"]}", "start": {segment["start"]}, "duration": {segment["duration"]}}},')
    print("]")
    
    print(f"\n# All videos scaled to: {TARGET_WIDTH}x{TARGET_HEIGHT}")
    print("# Original resolutions:")
    for segment in segments:
        print(f"# {segment['name']}: {segment['original_resolution']}")
    
    print("\n" + "="*60)
    
    # Also save to a file
    with open(os.path.join(VIDEO_FOLDER, "video_timings.txt"), "w") as f:
        f.write("VIDEO_SEGMENTS = [\n")
        for segment in segments:
            f.write(f'    {{"name": "{segment["name"]}", "start": {segment["start"]}, "duration": {segment["duration"]}}},\n')
        f.write("]\n\n")
        f.write(f"# All videos scaled to: {TARGET_WIDTH}x{TARGET_HEIGHT}\n")
        f.write("# Original resolutions:\n")
        for segment in segments:
            f.write(f"# {segment['name']}: {segment['original_resolution']}\n")
    
    print(f"Timings also saved to: {VIDEO_FOLDER}/video_timings.txt")

def verify_merged_video():
    """Verify the merged video was created successfully"""
    merged_path = os.path.join(VIDEO_FOLDER, MERGED_VIDEO)
    
    if not os.path.exists(merged_path):
        print(f"Error: Merged video not found at {merged_path}")
        return False
    
    # Get info about merged video
    info = get_video_info(merged_path)
    if info:
        print(f"\nMerged video:")
        print(f"  Resolution: {info['resolution']}")
        print(f"  Duration: {info['duration']:.1f} seconds")
        
        # Get file size
        file_size = os.path.getsize(merged_path)
        print(f"  Size: {file_size / (1024*1024):.1f} MB")
        
        return True
    else:
        print("Error getting merged video info")
        return False

def main():
    print("Video Merger and Timing Extractor")
    print("=" * 50)
    print(f"Target resolution: {TARGET_WIDTH}x{TARGET_HEIGHT}")
    print("=" * 50)
    
    # Check if ffmpeg and ffprobe are available
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        subprocess.run(["ffprobe", "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: ffmpeg and ffprobe are required but not found.")
        print("Install with: sudo apt install ffmpeg")
        return
    
    # Step 1: Extract timings from original videos
    segments = extract_timings()
    
    if not segments:
        print("No valid video segments found. Exiting.")
        return
    
    # Step 2: Merge videos with scaling
    if merge_videos():
        # Step 3: Verify merged video
        if verify_merged_video():
            # Step 4: Generate updated code
            generate_updated_code(segments)
            
            print(f"\n✅ Success! Merged video created: {VIDEO_FOLDER}/{MERGED_VIDEO}")
            print("✅ All videos scaled to consistent resolution")
            print("✅ Copy the VIDEO_SEGMENTS code above into your app.py file")
        else:
            print("❌ Error verifying merged video")
    else:
        print("❌ Error merging videos")

if __name__ == "__main__":
    main()