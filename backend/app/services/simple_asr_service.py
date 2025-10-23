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
    ASR service that tries Parakeet first (via Python 3.10), 
    then falls back to Google Speech Recognition
    """
    
    def __init__(self):
        """Initialize the ASR service."""
        self.model_ready = False
        self.use_parakeet = False
        self.model_name = "simple-speech-recognition"
        self.device = "cpu"
        self._check_parakeet()
        if not self.use_parakeet:
            self._try_load_basic_asr()
    
    def _check_parakeet(self):
        """Check if Parakeet is available via Python 3.10"""
        try:
            # Check if venv_asr exists and has the transcription script
            venv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'venv_asr')
            script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'transcribe_with_parakeet.py')
            python_exe = os.path.join(venv_path, 'Scripts', 'python.exe')
            
            if os.path.exists(python_exe) and os.path.exists(script_path):
                # Test if NeMo is installed
                test_cmd = [python_exe, '-c', 'import nemo.collections.asr; print("OK")']
                result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0 and 'OK' in result.stdout:
                    self.use_parakeet = True
                    self.model_ready = True
                    self.model_name = "nvidia/parakeet-tdt-0.6b-v2"
                    self.python_exe = python_exe
                    self.script_path = script_path
                    print("✅ Parakeet ASR available (Python 3.10)")
                    return
        except Exception as e:
            print(f"⚠️ Parakeet check failed: {e}")
        
        self.use_parakeet = False
    
    def _try_load_basic_asr(self):
        """Try to load basic speech recognition libraries."""
        try:
            import speech_recognition as sr
            import librosa
            import soundfile as sf
            
            self.recognizer = sr.Recognizer()
            self.model_ready = True
            print("✅ Google Speech Recognition loaded")
            
        except Exception as e:
            print(f"⚠️ Simple ASR service not available: {e}")
            self.model_ready = False
    
    def is_ready(self) -> bool:
        """Check if the ASR service is ready."""
        return self.model_ready
    
    def _transcribe_with_parakeet(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe using Parakeet via Python 3.10 subprocess
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dict with transcription results
        """
        print(f"🎤 Starting Parakeet transcription: {os.path.basename(audio_path)}")
        
        # Call Python 3.10 with the transcription script
        cmd = [self.python_exe, self.script_path, audio_path]
        
        # Run with timeout (5 minutes for long audio)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            raise Exception(f"Parakeet script failed: {result.stderr}")
        
        # Parse JSON output
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse Parakeet output: {e}\nOutput: {result.stdout[:500]}")
        
        if not data.get('success'):
            error_msg = data.get('error', 'Unknown error')
            raise Exception(f"Parakeet transcription failed: {error_msg}")
        
        print(f"✅ Parakeet transcription completed: {len(data.get('text', ''))} characters")
        print(f"   Model: {data.get('model')}, Device: {data.get('device')}")
        
        # Format segments from Parakeet timestamps
        segments = []
        for seg in data.get('segment_timestamps', []):
            segments.append({
                'text': seg.get('label', seg.get('segment', '')),
                'start': seg.get('start_offset', 0),
                'end': seg.get('end_offset', 0)
            })
        
        return {
            "full_text": data.get('text', ''),
            "segments": segments,
            "word_timestamps": data.get('word_timestamps', []),
            "asr_confidence": 0.95,  # Parakeet high confidence
            "model": data.get('model'),
            "device": data.get('device')
        }
    
    def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file using Parakeet (if available) or Google Speech Recognition.
        
        Args:
            audio_path: Path to the audio file to transcribe
            
        Returns:
            Dictionary containing transcription results
        """
        if not self.is_ready():
            raise Exception("ASR service is not available")
        
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Try Parakeet first
        if self.use_parakeet:
            try:
                return self._transcribe_with_parakeet(audio_path)
            except Exception as e:
                print(f"⚠️ Parakeet transcription failed: {e}")
                print("   Falling back to Google Speech Recognition...")
                # Fall through to Google Speech Recognition
        
        # Use Google Speech Recognition
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
                    "model_used": self.model_name,
                    "device_used": self.device
                }
            }
            
        except Exception as e:
            print(f"❌ Simple transcription failed: {e}")
            traceback.print_exc()
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
