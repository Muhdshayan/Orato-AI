import os
import subprocess
import sys
import whisper.audio

# Set FFmpeg path
FFMPEG_PATH = r"C:\ProgramData\chocolatey\bin\ffmpeg.exe"
os.environ["FFMPEG_BINARY"] = FFMPEG_PATH

# Patch whisper's audio loading to use our FFmpeg path
def patched_load_audio(file: str, sr: int = 16000):
    if isinstance(file, str):
        # If it's a file path, create the FFmpeg command
        cmd = [FFMPEG_PATH, "-nostdin", "-threads", "0", "-i", file, "-f", "s16le", "-ac", "1", "-acodec", "pcm_s16le", "-ar", str(sr), "-"]
        try:
            out = subprocess.run(cmd, capture_output=True, check=True).stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg failed: {e.stderr.decode()}") from e
        return np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0
    return original_load_audio(file, sr)

# Import numpy for audio processing
import numpy as np
original_load_audio = whisper.audio.load_audio
whisper.audio.load_audio = patched_load_audio

def install_requirements():
    print("Checking and installing required packages...")
    try:
        # Install whisper
        subprocess.check_call([sys.executable, "-m", "pip", "install", "openai-whisper"])
        print("All required packages installed successfully!")
    except Exception as e:
        print(f"Error installing packages: {str(e)}")
        sys.exit(1)

# Install requirements first
install_requirements()

# Now import whisper after ensuring it's installed
import whisper

SUPPORTED_FORMATS = ['.wav', '.mp3', '.m4a', '.ogg', '.flac']

def transcribe_audio(audio_path):
    # Check if file exists
    if not os.path.exists(audio_path):
        print(f"Error: Audio file not found at {audio_path}")
        return
    
    # Check file format
    file_extension = os.path.splitext(audio_path)[1].lower()
    if file_extension not in SUPPORTED_FORMATS:
        print(f"Error: Unsupported file format. Please use one of these formats: {', '.join(SUPPORTED_FORMATS)}")
        return
    
    print("Loading Whisper medium.en model (English optimized)...")
    model = whisper.load_model("medium.en")
    print("Transcribing audio...")
    
    # Use English-specific settings for better accuracy
    result = model.transcribe(audio_path, language='en')
    print("\nTranscription result:")
    print(result["text"])

if __name__ == "__main__":
    print("Supported audio formats:", ', '.join(SUPPORTED_FORMATS))
    
    # Ask for file path
    audio_file = input("Enter the path to your audio file: ")
    
    transcribe_audio(audio_file)