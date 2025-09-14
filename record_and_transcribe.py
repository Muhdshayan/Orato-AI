import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import os
import whisper
import tkinter as tk
from tkinter import ttk
import threading
import time

# Set FFmpeg path
FFMPEG_PATH = r"C:\ProgramData\chocolatey\bin\ffmpeg.exe"
os.environ["FFMPEG_BINARY"] = FFMPEG_PATH

class AudioRecorderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio Recorder & Transcriber")
        self.root.geometry("600x500")
        
        # Recording parameters
        self.sample_rate = 44100  # Standard audio sampling rate
        self.recording = False
        self.audio_data = []
        
        # Initialize whisper model (medium.en for English optimization)
        print("Loading Whisper model (medium.en)...")
        self.model = whisper.load_model("medium.en")
        
        self.create_widgets()
    
    def create_widgets(self):
        # Main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(self.main_frame, 
                               text="Voice Recorder & Transcriber", 
                               font=('Helvetica', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=10)
        
        # Record button
        self.record_button = ttk.Button(self.main_frame, 
                                      text="Start Recording", 
                                      command=self.toggle_recording)
        self.record_button.grid(row=1, column=0, columnspan=2, pady=10)
        
        # Recording status
        self.status_var = tk.StringVar(value="Ready to record")
        self.status_label = ttk.Label(self.main_frame, 
                                    textvariable=self.status_var,
                                    font=('Helvetica', 10))
        self.status_label.grid(row=2, column=0, columnspan=2, pady=5)
        
        # Timer display
        self.timer_var = tk.StringVar(value="00:00")
        self.timer_label = ttk.Label(self.main_frame, 
                                   textvariable=self.timer_var,
                                   font=('Helvetica', 24))
        self.timer_label.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Progress bar
        self.progress = ttk.Progressbar(self.main_frame, mode='indeterminate')
        self.progress.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Result frame
        result_frame = ttk.LabelFrame(self.main_frame, text="Transcription Result", padding="5")
        result_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
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
    
    def toggle_recording(self):
        if not self.recording:
            # Start recording
            self.recording = True
            self.record_button.configure(text="Stop Recording")
            self.status_var.set("Recording...")
            self.audio_data = []  # Clear previous recording
            
            # Start recording thread
            self.record_thread = threading.Thread(target=self.record_audio)
            self.record_thread.daemon = True
            self.record_thread.start()
            
            # Start timer
            self.start_time = time.time()
            self.update_timer()
        else:
            # Stop recording
            self.recording = False
            self.record_button.configure(text="Start Recording")
            self.status_var.set("Processing recording...")
            self.progress.start()
            
            # Process audio in separate thread
            process_thread = threading.Thread(target=self.process_audio)
            process_thread.daemon = True
            process_thread.start()
    
    def update_timer(self):
        if self.recording:
            elapsed = int(time.time() - self.start_time)
            minutes = elapsed // 60
            seconds = elapsed % 60
            self.timer_var.set(f"{minutes:02d}:{seconds:02d}")
            self.root.after(1000, self.update_timer)
    
    def record_audio(self):
        with sd.InputStream(samplerate=self.sample_rate, channels=1, callback=self.audio_callback):
            while self.recording:
                sd.sleep(100)
    
    def audio_callback(self, indata, frames, time, status):
        if status:
            print(status)
        self.audio_data.append(indata.copy())
    
    def process_audio(self):
        try:
            # Combine all audio chunks
            audio = np.concatenate(self.audio_data, axis=0)
            
            # Save as WAV file
            temp_wav = "temp_recording.wav"
            wav.write(temp_wav, self.sample_rate, audio)
            
            # Transcribe (using English-optimized settings)
            self.status_var.set("Transcribing audio...")
            result = self.model.transcribe(temp_wav, language='en')
            
            # Update GUI
            self.root.after(0, self.update_result, result["text"])
            
            # Clean up
            os.remove(temp_wav)
            
        except Exception as e:
            self.root.after(0, self.update_error, str(e))
        finally:
            self.root.after(0, self.cleanup)
    
    def update_result(self, text):
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, text)
        self.status_var.set("Transcription completed!")
        self.timer_var.set("00:00")
        self.progress.stop()
    
    def update_error(self, error_message):
        self.status_var.set(f"Error: {error_message}")
        self.progress.stop()
    
    def cleanup(self):
        self.progress.stop()
        self.status_var.set("Ready to record")

def main():
    # Install required packages
    try:
        import pip
        pip.main(['install', 'sounddevice', 'scipy', 'numpy', 'openai-whisper'])
    except Exception as e:
        print(f"Error installing packages: {e}")
        return

    root = tk.Tk()
    app = AudioRecorderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
