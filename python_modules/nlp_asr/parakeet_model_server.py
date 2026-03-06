"""
Parakeet Model Server - Keeps model loaded in memory for reuse.
This server runs as a separate process and provides transcription via inter-process communication.
"""
import os
import sys
import json
import signal
import socket
import threading
import traceback
import warnings
from typing import Optional

# Suppress warnings
warnings.filterwarnings('ignore')

# Fix Windows signal issue
if not hasattr(signal, 'SIGKILL'):
    signal.SIGKILL = signal.SIGTERM

class ParakeetModelServer:
    """Server that keeps Parakeet model loaded and handles transcription requests"""
    
    def __init__(self, socket_path: str):
        self.socket_path = socket_path
        self.model = None
        self.device = None
        self.model_name = "nvidia/parakeet-tdt-0.6b-v3"
        self.server_socket = None
        self.running = False
        
    def _setup_environment(self):
        """Setup cache and temp directories"""
        # Get project root (this file is in backend/app/services/)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        hf_cache = os.path.join(project_root, '.cache', 'huggingface')
        temp_dir = os.path.join(project_root, '.cache', 'temp')
        nemo_cache = os.path.join(project_root, '.cache', 'nemo_models')
        
        # Create directories
        os.makedirs(hf_cache, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)
        os.makedirs(nemo_cache, exist_ok=True)
        
        # Set environment variables
        os.environ['HF_HOME'] = hf_cache
        os.environ['HUGGINGFACE_HUB_CACHE'] = hf_cache
        # Enable offline mode to use cached models without network access
        os.environ['TRANSFORMERS_OFFLINE'] = '1'
        os.environ['HF_HUB_OFFLINE'] = '1'
        os.environ['TMPDIR'] = temp_dir
        os.environ['TEMP'] = temp_dir
        os.environ['TMP'] = temp_dir
        os.environ['NEMO_CACHE_DIR'] = nemo_cache
        os.environ['NEMO_EXTRACTION_DIR'] = nemo_cache
        os.environ['HYDRA_FULL_ERROR'] = '0'
        os.environ['OMP_NUM_THREADS'] = '1'
        os.environ['NEMO_LOG_LEVEL'] = 'ERROR'
        
        # Suppress logging
        import logging
        logging.basicConfig(level=logging.ERROR)
        for logger_name in ['nemo', 'pytorch_lightning', 'lightning', 'transformers', 'torch']:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.ERROR)
            logger.propagate = False
    
    def load_model(self):
        """Load the Parakeet model (called once at startup)"""
        if self.model is not None:
            print("Model already loaded", file=sys.stderr)
            return
        
        try:
            print(f"Loading Parakeet model: {self.model_name}", file=sys.stderr)
            self._setup_environment()
            
            import torch
            import nemo.collections.asr as nemo_asr
            
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            print(f"Device: {self.device}", file=sys.stderr)
            
            # Try to load from local cache first to avoid network requests
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            hf_cache = os.path.join(project_root, '.cache', 'huggingface')
            
            # Look for the model file in HuggingFace cache
            model_cache_path = os.path.join(hf_cache, 'models--nvidia--parakeet-tdt-0.6b-v3', 'snapshots')
            local_model_path = None
            
            if os.path.exists(model_cache_path):
                # Find the model file in snapshots directory
                for root, dirs, files in os.walk(model_cache_path):
                    for file in files:
                        if file.endswith('.nemo'):
                            local_model_path = os.path.join(root, file)
                            print(f"Found cached model at: {local_model_path}", file=sys.stderr)
                            break
                    if local_model_path:
                        break
            
            # Load model from local path if found, otherwise use from_pretrained
            if local_model_path and os.path.exists(local_model_path):
                print(f"Loading model from local cache: {local_model_path}", file=sys.stderr)
                # Use restore_from to load from local .nemo file
                self.model = nemo_asr.models.ASRModel.restore_from(restore_path=local_model_path)
                self.model.to(self.device)
            else:
                print("Loading model from HuggingFace (offline mode)...", file=sys.stderr)
                # Use from_pretrained with offline mode - it should use cached version
                self.model = nemo_asr.models.ASRModel.from_pretrained(model_name=self.model_name)
                self.model.to(self.device)
            
            print("✅ Model loaded successfully", file=sys.stderr)
            
        except Exception as e:
            print(f"❌ Failed to load model: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            raise
    
    def transcribe(self, audio_path: str) -> dict:
        """Transcribe audio file using loaded model"""
        if self.model is None:
            raise Exception("Model not loaded")
        
        try:
            import librosa
            import soundfile as sf
            import numpy as np
            import torch
            import tempfile
            
            # Load audio
            audio, sr = librosa.load(audio_path, sr=16000, mono=True)
            duration = len(audio) / sr
            
            # Save as temporary mono WAV file
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            temp_dir = os.path.join(project_root, '.cache', 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            
            with tempfile.NamedTemporaryFile(dir=temp_dir, suffix='.wav', delete=False) as tmp_file:
                mono_audio_path = tmp_file.name
                sf.write(mono_audio_path, audio, sr)
            
            try:
                # Transcribe
                transcription = self.model.transcribe([mono_audio_path], return_hypotheses=True)
                
                # Extract results
                hypothesis = transcription[0][0] if isinstance(transcription[0], list) else transcription[0]
                full_text = hypothesis.text
                
                # Extract timestamps
                segments = []
                try:
                    timestep = hypothesis.timestep
                    words = hypothesis.words if hasattr(hypothesis, 'words') else full_text.split()
                    
                    if isinstance(timestep, torch.Tensor):
                        timestep_array = timestep.cpu().numpy() if timestep.is_cuda else timestep.numpy()
                    else:
                        timestep_array = np.array(timestep)
                    
                    frame_duration = 0.08  # 80ms per encoder frame (8x subsampling of 10ms raw frames)

                    words_per_segment = 15
                    
                    if len(timestep_array) > 0 and len(words) > 0:
                        frames_per_word = len(timestep_array) / len(words)
                        
                        word_timestamps = []
                        for i, word in enumerate(words):
                            start_frame = int(i * frames_per_word)
                            end_frame = int((i + 1) * frames_per_word)
                            start_frame = min(start_frame, len(timestep_array) - 1)
                            end_frame = min(end_frame, len(timestep_array))
                            
                            if end_frame > start_frame:
                                actual_start_frame = int(timestep_array[start_frame])
                                actual_end_frame = int(timestep_array[min(end_frame - 1, len(timestep_array) - 1)])
                            else:
                                actual_start_frame = int(timestep_array[start_frame])
                                actual_end_frame = actual_start_frame
                            
                            start_time = actual_start_frame * frame_duration
                            end_time = actual_end_frame * frame_duration
                            
                            word_timestamps.append({
                                'word': word,
                                'start': round(start_time, 3),
                                'end': round(end_time, 3)
                            })
                        
                        # Create segments
                        for i in range(0, len(word_timestamps), words_per_segment):
                            segment_words = word_timestamps[i:i + words_per_segment]
                            if segment_words:
                                segments.append({
                                    'text': ' '.join([w['word'] for w in segment_words]),
                                    'start': round(segment_words[0]['start'], 3),
                                    'end': round(segment_words[-1]['end'], 3)
                                })
                    
                except Exception as e:
                    print(f"Warning: Timestamp extraction failed: {e}", file=sys.stderr)
                    # Fallback segments
                    words = full_text.split()
                    words_per_segment = 15
                    segment_duration = duration / max(1, len(words) / words_per_segment)
                    
                    for i in range(0, len(words), words_per_segment):
                        segment_words = words[i:i + words_per_segment]
                        segment_idx = i // words_per_segment
                        segments.append({
                            'text': ' '.join(segment_words),
                            'start': round(segment_idx * segment_duration, 3),
                            'end': round((segment_idx + 1) * segment_duration, 3)
                        })
                
                word_count = len(full_text.split())
                
                return {
                    'success': True,
                    'text': full_text,
                    'segment_timestamps': segments,
                    'model': self.model_name,
                    'device': self.device,
                    'audio_duration': round(duration, 2),
                    'word_count': word_count
                }
                
            finally:
                # Clean up temp file
                try:
                    if os.path.exists(mono_audio_path):
                        os.remove(mono_audio_path)
                except:
                    pass
                    
        except Exception as e:
            error_msg = str(e)
            print(f"Transcription error: {error_msg}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return {
                'success': False,
                'error': error_msg,
                'text': '',
                'segment_timestamps': []
            }
    
    def start_server(self):
        """Start the model server and listen for requests"""
        # Remove old socket if it exists
        if os.path.exists(self.socket_path):
            try:
                os.remove(self.socket_path)
            except:
                pass
        
        # Create Unix domain socket (Windows: use named pipe)
        if sys.platform == 'win32':
            # Windows: Use localhost TCP socket instead
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('127.0.0.1', 8765))  # Fixed port for model server
        else:
            # Unix: Use domain socket
            self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.server_socket.bind(self.socket_path)
        
        self.server_socket.listen(5)
        self.running = True
        
        print(f"Model server listening on {self.socket_path if sys.platform != 'win32' else '127.0.0.1:8765'}", file=sys.stderr)
        
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                threading.Thread(target=self._handle_client, args=(client_socket,), daemon=True).start()
            except Exception as e:
                if self.running:
                    print(f"Server error: {e}", file=sys.stderr)
    
    def _handle_client(self, client_socket):
        """Handle a client request"""
        try:
            # Read request
            data = b''
            while True:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b'\n\n' in data:  # End of request marker
                    break
            
            if not data:
                return
            
            request = json.loads(data.decode('utf-8').strip())
            audio_path = request.get('audio_path')
            
            if not audio_path or not os.path.exists(audio_path):
                response = {
                    'success': False,
                    'error': f'Audio file not found: {audio_path}'
                }
            else:
                response = self.transcribe(audio_path)
            
            # Send response
            response_json = json.dumps(response) + '\n\n'
            client_socket.sendall(response_json.encode('utf-8'))
            
        except Exception as e:
            error_response = {
                'success': False,
                'error': str(e)
            }
            try:
                response_json = json.dumps(error_response) + '\n\n'
                client_socket.sendall(response_json.encode('utf-8'))
            except:
                pass
        finally:
            client_socket.close()
    
    def stop_server(self):
        """Stop the server"""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass


def start_model_server():
    """Entry point to start the model server"""
    # Get project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Socket path
    if sys.platform == 'win32':
        socket_path = os.path.join(project_root, '.cache', 'parakeet_server.sock')
    else:
        socket_path = os.path.join(project_root, '.cache', 'parakeet_server.sock')
    
    server = ParakeetModelServer(socket_path)
    
    # Load model
    try:
        server.load_model()
    except Exception as e:
        print(f"Failed to load model: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Handle shutdown
    def signal_handler(sig, frame):
        print("\nShutting down model server...", file=sys.stderr)
        server.stop_server()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start server
    server.start_server()


if __name__ == '__main__':
    start_model_server()

