import subprocess
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
    """Get video information"""
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
        
        return {"duration": duration, "resolution": resolution}
    except Exception as e:
        print(f"Error getting info for {video_path}: {e}")
        return None

def simple_merge():
    """Simple merge using file list method"""
    print("Creating simple merge using file concatenation...")
    
    os.chdir(VIDEO_FOLDER)
    
    # Check all files exist
    for video_file in VIDEO_FILES:
        if not os.path.exists(video_file):
            print(f"Missing: {video_file}")
            return False
        
        info = get_video_info(video_file)
        if info:
            print(f"{video_file}: {info['resolution']} - {info['duration']:.1f}s")
    
    # Create file list for ffmpeg
    with open("filelist.txt", "w") as f:
        for video_file in VIDEO_FILES:
            f.write(f"file '{video_file}'\n")
    
    # Simple concat using file list (works better with different formats)
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "filelist.txt",
        "-c", "copy",  # Copy streams without re-encoding (faster)
        MERGED_VIDEO
    ]
    
    print("Running simple merge (copy mode)...")
    print(" ".join(cmd))
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"SUCCESS: Simple merge successful!")
        
        # Clean up
        os.remove("filelist.txt")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Simple merge failed: {e}")
        print(f"Stderr: {e.stderr}")
        
        # Try with re-encoding if copy failed
        print("Trying with re-encoding...")
        return reencode_merge()

def reencode_merge():
    """Merge with re-encoding to handle format differences"""
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "filelist.txt",
        "-c:v", "libx264", "-c:a", "aac",
        "-preset", "fast",  # Faster encoding
        "-crf", "23",
        MERGED_VIDEO
    ]
    
    print("Running re-encode merge...")
    print(" ".join(cmd))
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"SUCCESS: Re-encode merge successful!")
        
        # Clean up
        if os.path.exists("filelist.txt"):
            os.remove("filelist.txt")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Re-encode merge failed: {e}")
        print(f"Stderr: {e.stderr}")
        return False

def verify_and_get_timings():
    """Verify merged video and generate timings"""
    merged_path = os.path.join(VIDEO_FOLDER, MERGED_VIDEO)
    
    if not os.path.exists(merged_path):
        print("ERROR: Merged video not found")
        return
    
    # Check merged video
    info = get_video_info(merged_path)
    if info:
        file_size = os.path.getsize(merged_path) / (1024*1024)
        print(f"\nSUCCESS: Merged video: {info['resolution']} - {info['duration']:.1f}s - {file_size:.1f}MB")
        
        # Generate timings from original videos
        segments = []
        current_start = 0
        
        for i, video_file in enumerate(VIDEO_FILES):
            orig_info = get_video_info(video_file)
            
            if orig_info:
                segment = {
                    "name": f"video{i+1}",
                    "start": round(current_start, 1),
                    "duration": round(orig_info["duration"], 1)
                }
                segments.append(segment)
                current_start += orig_info["duration"]
        
        if segments:
            print("\n" + "="*60)
            print("COPY THIS INTO YOUR app.py FILE:")
            print("="*60)
            
            print("VIDEO_SEGMENTS = [")
            for segment in segments:
                print(f'    {{"name": "{segment["name"]}", "start": {segment["start"]}, "duration": {segment["duration"]}}},')
            print("]")
            
            print("\n" + "="*60)
            
            # Save to file
            with open("video_timings.txt", "w") as f:
                f.write("VIDEO_SEGMENTS = [\n")
                for segment in segments:
                    f.write(f'    {{"name": "{segment["name"]}", "start": {segment["start"]}, "duration": {segment["duration"]}}},\n')
                f.write("]\n")
            
            print("SUCCESS: Timings saved to video_timings.txt")
    else:
        print("ERROR: Could not verify merged video")

def main():
    print("Simple Video Merger")
    print("=" * 30)
    
    if simple_merge():
        verify_and_get_timings()
    else:
        print("ERROR: Merge failed")

if __name__ == "__main__":
    main()
