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

def get_video_duration(video_path):
    """Get duration of a video file in seconds"""
    try:
        result = subprocess.run([
            "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", video_path
        ], capture_output=True, text=True, check=True)
        
        duration = float(result.stdout.strip())
        return duration
    except Exception as e:
        print(f"Error getting duration for {video_path}: {e}")
        return 0

def merge_videos():
    """Merge all videos into one file"""
    print("Merging videos...")
    
    # Change to video directory
    os.chdir(VIDEO_FOLDER)
    
    # Check if all video files exist
    missing_files = []
    for video_file in VIDEO_FILES:
        if not os.path.exists(video_file):
            missing_files.append(video_file)
    
    if missing_files:
        print(f"Missing video files: {missing_files}")
        return False
    
    # Build ffmpeg command for merging
    input_args = []
    for video_file in VIDEO_FILES:
        input_args.extend(["-i", video_file])
    
    # Create filter complex for concatenation
    filter_complex = ""
    for i in range(len(VIDEO_FILES)):
        filter_complex += f"[{i}:v][{i}:a]"
    filter_complex += f"concat=n={len(VIDEO_FILES)}:v=1:a=1[outv][outa]"
    
    # Full ffmpeg command
    ffmpeg_cmd = [
        "ffmpeg", "-y"  # -y to overwrite existing file
    ] + input_args + [
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-c:a", "aac",  # Ensure compatible codecs
        MERGED_VIDEO
    ]
    
    try:
        print("Running ffmpeg merge command...")
        result = subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
        print(f"Successfully merged videos into {MERGED_VIDEO}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error merging videos: {e}")
        print(f"FFmpeg stderr: {e.stderr}")
        return False

def extract_timings():
    """Extract timing information for each video segment"""
    print("\nExtracting video timings...")
    
    segments = []
    current_start = 0
    
    for i, video_file in enumerate(VIDEO_FILES):
        video_path = os.path.join(VIDEO_FOLDER, video_file)
        duration = get_video_duration(video_path)
        
        if duration > 0:
            segment = {
                "name": f"video{i+1}",
                "start": round(current_start, 1),
                "duration": round(duration, 1),
                "end": round(current_start + duration, 1)
            }
            segments.append(segment)
            current_start += duration
            
            print(f"{video_file}: Duration = {duration:.1f}s")
        else:
            print(f"Could not get duration for {video_file}")
    
    return segments

def generate_updated_code(segments):
    """Generate the updated Python code with correct timings"""
    print("\n" + "="*50)
    print("COPY THIS INTO YOUR app.py FILE:")
    print("="*50)
    
    print("# Updated VIDEO_SEGMENTS with correct timings:")
    print("VIDEO_SEGMENTS = [")
    for segment in segments:
        print(f'    {{"name": "{segment["name"]}", "start": {segment["start"]}, "duration": {segment["duration"]}}},')
    print("]")
    
    print("\n" + "="*50)
    
    # Also save to a file
    with open(os.path.join(VIDEO_FOLDER, "video_timings.txt"), "w") as f:
        f.write("VIDEO_SEGMENTS = [\n")
        for segment in segments:
            f.write(f'    {{"name": "{segment["name"]}", "start": {segment["start"]}, "duration": {segment["duration"]}}},\n')
        f.write("]\n")
    
    print(f"Timings also saved to: {VIDEO_FOLDER}/video_timings.txt")

def verify_merged_video():
    """Verify the merged video was created successfully"""
    merged_path = os.path.join(VIDEO_FOLDER, MERGED_VIDEO)
    
    if not os.path.exists(merged_path):
        print(f"Error: Merged video not found at {merged_path}")
        return False
    
    # Get duration of merged video
    merged_duration = get_video_duration(merged_path)
    print(f"\nMerged video duration: {merged_duration:.1f} seconds")
    
    # Get file size
    file_size = os.path.getsize(merged_path)
    print(f"Merged video size: {file_size / (1024*1024):.1f} MB")
    
    return True

def main():
    print("Video Merger and Timing Extractor")
    print("=" * 40)
    
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
    
    # Step 2: Merge videos
    if merge_videos():
        # Step 3: Verify merged video
        if verify_merged_video():
            # Step 4: Generate updated code
            generate_updated_code(segments)
            
            print(f"\n✅ Success! Merged video created: {VIDEO_FOLDER}/{MERGED_VIDEO}")
            print("✅ Copy the VIDEO_SEGMENTS code above into your app.py file")
        else:
            print("❌ Error verifying merged video")
    else:
        print("❌ Error merging videos")

if __name__ == "__main__":
    main()