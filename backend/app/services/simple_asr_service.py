import os
import json
import tempfile
import traceback
import subprocess
from typing import Dict, List, Any, Optional
from app.core.database import execute_query
from app.core.config import settings
import psycopg2
from psycopg2.extras import RealDictCursor

class SimpleASRService:
    """
    ASR service that tries Parakeet first (via Python 3.10 subprocess), 
    then falls back to Google Speech Recognition
    """
    
    def __init__(self):
        """Initialize the ASR service with paths (no pre-checks)."""
        # Get project root (4 levels up: services -> app -> backend -> root)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        # Set HuggingFace cache to project directory (D: drive)
        hf_cache = os.path.join(project_root, '.cache', 'huggingface')
        temp_dir = os.path.join(project_root, '.cache', 'temp')
        
        # Create directories if they don't exist
        os.makedirs(hf_cache, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)
        
        # Set cache and temp locations to D: drive (prevents C: drive usage)
        os.environ['HF_HOME'] = hf_cache
        os.environ['HUGGINGFACE_HUB_CACHE'] = hf_cache
        os.environ['TMPDIR'] = temp_dir
        os.environ['TEMP'] = temp_dir
        os.environ['TMP'] = temp_dir
        
        # Set paths for Parakeet subprocess call
        self.project_root = project_root
        venv_path = os.path.join(project_root, 'venv_asr')
        services_dir = os.path.dirname(__file__)
        
        self.python_exe = os.path.join(venv_path, 'Scripts', 'python.exe')
        self.script_path = os.path.join(services_dir, 'transcribe_with_parakeet.py')
        
        # Load Google Speech Recognition as fallback
        try:
            import speech_recognition as sr
            import librosa
            import soundfile as sf
            self.recognizer = sr.Recognizer()
            print("✅ Simple ASR service initialized (will try Parakeet first)")
        except Exception as e:
            print(f"⚠️ Google Speech Recognition not available: {e}")
            self.recognizer = None
    
    def is_ready(self) -> bool:
        """Check if the ASR service is ready."""
        return True  # Always ready (will try Parakeet, then fallback if needed)
    
    def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file - tries Parakeet first, falls back to Google Speech Recognition.
        
        Args:
            audio_path: Path to the audio file to transcribe
            
        Returns:
            Dictionary containing transcription results
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # ALWAYS TRY PARAKEET FIRST (via model server, falls back to subprocess)
        try:
            print(f"🎤 Attempting Parakeet transcription: {os.path.basename(audio_path)}")
            
            # Use Parakeet client (tries model server first, falls back to subprocess)
            from app.services.parakeet_client import parakeet_client
            data = parakeet_client.transcribe(audio_path)
            
            if not data.get('success'):
                error_msg = data.get('error', 'Unknown error')
                raise Exception(f"Parakeet transcription failed: {error_msg}")
            
            print(f"✅ Parakeet transcription completed: {len(data.get('text', ''))} characters")
            print(f"   Model: {data.get('model')}, Device: {data.get('device')}")
            
            # Format segments from Parakeet timestamps (new format)
            segments = data.get('segment_timestamps', [])
            
            return {
                "full_text": data.get('text', ''),
                "segments": segments,  # Already in correct format: {text, start, end}
                "asr_confidence": 0.95,  # Parakeet high confidence
                "asr_metadata": {
                    "audio_duration": data.get('audio_duration', 0),
                    "word_count": data.get('word_count', 0),
                    "model_used": data.get('model', 'nvidia/parakeet-tdt-0.6b-v3'),
                    "device_used": data.get('device', 'unknown')
                }
            }
            
        except Exception as e:
            print(f"❌ Parakeet transcription failed: {e}")
            traceback.print_exc()
            
            # FALLBACK TO GOOGLE SPEECH RECOGNITION (COMMENTED OUT FOR DEBUGGING)
            # Uncomment the block below when ready to enable fallback
            """
            print("⚠️ Falling back to Google Speech Recognition...")
            try:
                print(f"🎤 Starting Google Speech transcription: {os.path.basename(audio_path)}")
                
                # Convert audio to WAV format for speech recognition
                wav_path = self._convert_to_wav(audio_path)
                
                # Transcribe using Google Speech Recognition
                import speech_recognition as sr
                
                with sr.AudioFile(wav_path) as source:
                    audio_data = self.recognizer.record(source)
                
                # Get transcription
                full_text = self.recognizer.recognize_google(audio_data)
                
                # Clean up temporary file
                if wav_path != audio_path and os.path.exists(wav_path):
                    os.remove(wav_path)
                
                print(f"✅ Google transcription completed: {len(full_text)} characters")
                
                return {
                    "full_text": full_text,
                    "segments": [],  # Not available in simple mode
                    "asr_confidence": 0.8,  # Default confidence for simple mode
                    "asr_metadata": {
                        "audio_duration": self._get_audio_duration(audio_path),
                        "model_used": "simple-speech-recognition",
                        "device_used": "cpu"
                    }
                }
            except Exception as google_error:
                print(f"❌ Google transcription also failed: {google_error}")
                traceback.print_exc()
                raise
            """
            # Re-raise the Parakeet error since fallback is disabled
            raise
    
    def _convert_to_wav(self, audio_path: str) -> str:
        """Convert audio file to WAV format."""
        try:
            import librosa
            import soundfile as sf
            
            # Load audio
            audio, sr = librosa.load(audio_path, sr=16000)  # 16kHz sample rate
            
            # Create temporary WAV file
            base, ext = os.path.splitext(audio_path)
            wav_path = f"{base}_temp.wav"
            
            # Save as WAV
            sf.write(wav_path, audio, sr)
            
            return wav_path
            
        except Exception as e:
            print(f"⚠️ Audio conversion failed, using original: {e}")
            return audio_path
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """Get the duration of an audio file in seconds."""
        try:
            import librosa
            audio, sr = librosa.load(audio_path)
            return len(audio) / sr
        except:
            return 0.0
    
    def store_transcript(self, submission_id: str, transcript_data: Dict[str, Any]) -> str:
        """Store transcription results in the database."""
        try:
            print(f"💾 Storing simple transcript for submission: {submission_id}")
            
            query = """
            INSERT INTO transcripts (submission_id, text, segments, 
                                   asr_confidence, asr_metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING transcript_id
            """
            
            # For JSONB columns, psycopg2 with RealDictCursor handles dict/list conversion automatically
            # We can pass Python dicts/lists directly
            result = execute_query(
                query,
                (
                    submission_id,
                    transcript_data["full_text"],
                    transcript_data["segments"],  # Pass list directly for JSONB
                    transcript_data["asr_confidence"],
                    transcript_data["asr_metadata"]  # Pass dict directly for JSONB
                ),
                fetch_one=True
            )
            
            transcript_id = result["transcript_id"]
            print(f"✅ Simple transcript stored with ID: {transcript_id}")
            
            return transcript_id
            
        except Exception as e:
            print(f"❌ Failed to store simple transcript: {e}")
            traceback.print_exc()
            raise
    
    def get_transcript(self, submission_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve transcript from database."""
        try:
            query = """
            SELECT transcript_id, text, segments, asr_confidence, asr_metadata, created_at
            FROM transcripts
            WHERE submission_id = %s
            ORDER BY created_at DESC
            LIMIT 1
            """
            
            result = execute_query(query, (submission_id,), fetch_one=True)
            
            if result:
                # JSONB columns are already returned as Python dicts by psycopg2
                # Only parse if they're strings (shouldn't happen with JSONB, but be safe)
                segments = result["segments"]
                if isinstance(segments, str):
                    segments = json.loads(segments)
                elif segments is None:
                    segments = []
                
                asr_metadata = result["asr_metadata"]
                if isinstance(asr_metadata, str):
                    asr_metadata = json.loads(asr_metadata)
                elif asr_metadata is None:
                    asr_metadata = {}
                
                return {
                    "transcript_id": result["transcript_id"],
                    "full_text": result["text"],
                    "segments": segments,
                    "asr_confidence": result["asr_confidence"],
                    "asr_metadata": asr_metadata,
                    "created_at": result["created_at"]
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Failed to retrieve simple transcript: {e}")
            return None

# Global simple ASR service instance
simple_asr_service = SimpleASRService()
