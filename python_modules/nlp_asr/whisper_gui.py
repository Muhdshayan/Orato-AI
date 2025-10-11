import tkinter as tk
from tkinter import filedialog, ttk
import threading
import os
import sys
import subprocess
import warnings
warnings.filterwarnings("ignore")  # Hide FP16 warning

# Set FFmpeg path
FFMPEG_PATH = r"C:\ProgramData\chocolatey\bin\ffmpeg.exe"
os.environ["FFMPEG_BINARY"] = FFMPEG_PATH

# Patch whisper's audio loading to use our FFmpeg path
import whisper.audio
import numpy as np

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

original_load_audio = whisper.audio.load_audio
whisper.audio.load_audio = patched_load_audio

class WhisperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio Transcription")
        self.root.geometry("600x500")
        
        # Create main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        
        # Initialize variables
        self.model = None
        self.model_loaded = False
        
        # Create widgets
        self.create_widgets()
        
        # Check and install requirements
        self.check_ffmpeg()

    def create_widgets(self):
        # Title
        title_label = ttk.Label(self.main_frame, text="Audio Transcription Tool", font=('Helvetica', 16, 'bold'))
        title_label.grid(row=0, column=0, pady=10)

        # File selection frame
        file_frame = ttk.LabelFrame(self.main_frame, text="Select Audio File", padding="5")
        file_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        file_frame.columnconfigure(0, weight=1)

        # File path entry and browse button
        self.file_path = tk.StringVar()
        self.file_entry = ttk.Entry(file_frame, textvariable=self.file_path)
        self.file_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5)
        
        self.browse_button = ttk.Button(file_frame, text="Browse", command=self.browse_file)
        self.browse_button.grid(row=0, column=1, padx=5)

        # Supported formats label
        formats_label = ttk.Label(file_frame, 
                                text="Supported formats: .wav, .mp3, .m4a, .ogg, .flac",
                                font=('Helvetica', 8))
        formats_label.grid(row=1, column=0, columnspan=2, pady=5)

        # Transcribe button
        self.transcribe_button = ttk.Button(self.main_frame, 
                                          text="Transcribe Audio",
                                          command=self.start_transcription)
        self.transcribe_button.grid(row=2, column=0, pady=10)

        # Progress bar
        self.progress = ttk.Progressbar(self.main_frame, mode='indeterminate')
        self.progress.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)

        # Status label
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(self.main_frame, textvariable=self.status_var, wraplength=550)
        self.status_label.grid(row=4, column=0, pady=5)

        # Result frame
        result_frame = ttk.LabelFrame(self.main_frame, text="Transcription Result", padding="5")
        result_frame.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)

        # Result text area with scrollbar
        self.result_text = tk.Text(result_frame, wrap=tk.WORD, height=12)
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scrollbar.set)
        
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Configure main frame grid
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(5, weight=1)

    def check_ffmpeg(self):
        """Check if ffmpeg is installed and install if needed"""
        try:
            # Try importing whisper first
            import whisper
            self.whisper = whisper
            
            # Try running ffmpeg
            ffmpeg_path = r"C:\ProgramData\chocolatey\bin\ffmpeg.exe"
            subprocess.run([ffmpeg_path, '-version'], capture_output=True, check=True)
            self.status_var.set("Ready - All requirements installed")
            
        except ImportError:
            self.status_var.set("Installing Whisper...")
            self.progress.start()
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "openai-whisper"])
                import whisper
                self.whisper = whisper
                self.status_var.set("Whisper installed successfully!")
            except Exception as e:
                self.status_var.set(f"Error installing Whisper: {str(e)}")
            finally:
                self.progress.stop()
                
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.status_var.set("Installing ffmpeg...")
            self.progress.start()
            try:
                # Install ffmpeg using pip
                subprocess.check_call([sys.executable, "-m", "pip", "install", "ffmpeg-python"])
                
                # On Windows, also try installing via chocolatey if available
                if os.name == 'nt':
                    try:
                        subprocess.run(['choco', '--version'], capture_output=True, check=True)
                        subprocess.run(['choco', 'install', 'ffmpeg', '-y'], check=True)
                    except:
                        self.status_var.set("Please install ffmpeg manually from: https://ffmpeg.org/download.html")
                        return
                
                self.status_var.set("ffmpeg installed successfully!")
            except Exception as e:
                self.status_var.set(f"Error installing ffmpeg: {str(e)}\nPlease install ffmpeg manually from: https://ffmpeg.org/download.html")
            finally:
                self.progress.stop()

    def browse_file(self):
        filetypes = (
            ('Audio files', '*.wav *.mp3 *.m4a *.ogg *.flac'),
            ('All files', '*.*')
        )
        filename = filedialog.askopenfilename(
            title='Select an audio file',
            filetypes=filetypes
        )
        if filename:
            self.file_path.set(filename)

    def start_transcription(self):
        if not self.file_path.get():
            self.status_var.set("Please select an audio file first!")
            return
            
        if not os.path.exists(self.file_path.get()):
            self.status_var.set("Selected file does not exist!")
            return

        # Disable buttons during transcription
        self.transcribe_button.state(['disabled'])
        self.browse_button.state(['disabled'])
        
        # Start progress bar
        self.progress.start()
        
        # Create and start transcription thread
        thread = threading.Thread(target=self.transcribe)
        thread.daemon = True
        thread.start()

    def transcribe(self):
        try:
            if not self.model_loaded:
                self.status_var.set("Loading Whisper model...")
                self.model = self.whisper.load_model("medium")
                self.model_loaded = True

            self.status_var.set("Transcribing audio...")
            result = self.model.transcribe(self.file_path.get())
            
            # Update GUI with result
            self.root.after(0, self.update_result, result['text'])
            
        except Exception as e:
            self.root.after(0, self.update_error, str(e))
            
        finally:
            # Stop progress and re-enable buttons
            self.root.after(0, self.cleanup)

    def update_result(self, text):
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, text)
        self.status_var.set("Transcription completed!")

    def update_error(self, error_message):
        self.status_var.set(f"Error: {error_message}")

    def cleanup(self):
        self.progress.stop()
        self.transcribe_button.state(['!disabled'])
        self.browse_button.state(['!disabled'])

def main():
    root = tk.Tk()
    app = WhisperGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()