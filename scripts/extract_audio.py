import os
import sys
import subprocess

def extract_audio(video_path, output_audio_path=None):
    if not os.path.exists(video_path):
        print(f"Error: Video file not found at '{video_path}'")
        sys.exit(1)
        
    if output_audio_path is None:
        # Default output path based on video filename
        base, _ = os.path.splitext(video_path)
        output_audio_path = f"{base}.wav"
        
    print(f"Extracting audio from: {video_path}")
    print(f"Output will be saved to: {output_audio_path}")
    
    # We use ffmpeg to extract, formatted for ASR (16kHz, mono, PCM 16-bit)
    command = [
        "ffmpeg", 
        "-y", # Overwrite output if exists
        "-i", video_path,
        "-vn", # Disable video stream
        "-acodec", "pcm_s16le", # PCM 16-bit
        "-ar", "16000", # 16kHz sampling rate
        "-ac", "1", # Mono
        output_audio_path
    ]
    
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"✅ Successfully extracted audio to: {os.path.abspath(output_audio_path)}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to extract audio. FFmpeg error:\n{e.stderr.decode('utf-8')}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_audio.py <path_to_video> [path_to_output_audio]")
        sys.exit(1)
        
    video_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    extract_audio(video_file, output_file)
