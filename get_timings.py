import subprocess
import os

# === Configuration ===
VIDEO_FOLDER = "/home/pi-five/pi_video"
VIDEO_FILES = [
    "video1.mp4",
    "video2.mp4", 
    "video3.mp4"
]

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

def get_video_resolution(video_path):
    """Get video resolution"""
    try:
        result = subprocess.run([
            "ffprobe", "-v", "quiet", "-select_streams", "v:0", 
            "-show_entries", "stream=width,height",
            "-of", "csv=s=x:p=0", video_path
        ], capture_output=True, text=True, check=True)
        
        return result.stdout.strip()
    except Exception as e:
        print(f"Error getting resolution for {video_path}: {e}")
        return "unknown"

def main():
    print("Video Timing Extractor")
    print("=" * 40)
    
    segments = []
    current_start = 0
    
    for i, video_file in enumerate(VIDEO_FILES):
        video_path = os.path.join(VIDEO_FOLDER, video_file)
        
        if os.path.exists(video_path):
            duration = get_video_duration(video_path)
            resolution = get_video_resolution(video_path)
            
            if duration > 0:
                segment = {
                    "name": f"video{i+1}",
                    "start": round(current_start, 1),
                    "duration": round(duration, 1)
                }
                segments.append(segment)
                current_start += duration
                
                print(f"{video_file}: {resolution} - {duration:.1f}s")
            else:
                print(f"Could not get duration for {video_file}")
        else:
            print(f"File not found: {video_file}")
    
    if segments:
        print("\n" + "="*60)
        print("COPY THIS INTO YOUR app.py FILE:")
        print("="*60)
        
        print("VIDEO_SEGMENTS = [")
        for segment in segments:
            print(f'    {{"name": "{segment["name"]}", "start": {segment["start"]}, "duration": {segment["duration"]}}},')
        print("]")
        
        print("\n" + "="*60)
        
        # Check merged video
        merged_path = os.path.join(VIDEO_FOLDER, "merged_videos.mp4")
        if os.path.exists(merged_path):
            merged_duration = get_video_duration(merged_path)
            merged_resolution = get_video_resolution(merged_path)
            file_size = os.path.getsize(merged_path) / (1024*1024)
            
            print(f"✅ Merged video exists: {merged_resolution} - {merged_duration:.1f}s - {file_size:.1f}MB")
        else:
            print("❌ Merged video not found")
    else:
        print("No valid video segments found")

if __name__ == "__main__":
    main()