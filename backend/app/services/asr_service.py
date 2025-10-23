import os
import json
import tempfile
import shutil
import traceback
from typing import Dict, List, Any, Optional
import torch
import nemo.collections.asr as nemo_asr
import soundfile as sf
import numpy as np
from app.core.database import execute_query
from app.core.config import settings
import psycopg2
from psycopg2.extras import RealDictCursor

class ASRService:
    """
    Audio-to-Text transcription service using NVIDIA NeMo Parakeet ASR model.
    This service handles audio file processing, transcription, and database storage.
    """
    
    def __init__(self):
        """Initialize the ASR service and load the model."""
        self.model = None
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model_name = "nvidia/parakeet-tdt-0.6b-v2"
        self._load_model()
    
    def _load_model(self):
        """
        Load the NVIDIA NeMo Parakeet ASR model.
        This method loads the pre-trained model for English speech recognition.
        """
        try:
            print(f"🔧 Loading ASR model: {self.model_name}")
            print(f"🔧 Device: {self.device}")
            
            # Load the pre-trained model
            self.model = nemo_asr.models.ASRModel.from_pretrained(
                model_name=self.model_name
            )
            self.model.to(self.device)
            
            print("✅ ASR model loaded successfully")
            
        except Exception as e:
            print(f"❌ Failed to load ASR model: {e}")
            traceback.print_exc()
            self.model = None
    
    def is_ready(self) -> bool:
        """Check if the ASR model is ready for transcription."""
        return self.model is not None
    
    def ensure_mono_audio(self, audio_path: str) -> str:
        """
        Convert stereo audio to mono if needed.
        NeMo models work best with mono audio files.
        
        Args:
            audio_path: Path to the input audio file
            
        Returns:
            Path to the mono audio file (original if already mono)
        """
        try:
            # Read the audio file
            signal, sample_rate = sf.read(audio_path)
            
            # Check if audio is stereo (2 channels)
            if signal.ndim > 1 and signal.shape[1] == 2:
                print(f"🔧 Converting stereo to mono: {os.path.basename(audio_path)}")
                
                # Convert to mono by averaging channels
                mono_signal = np.mean(signal, axis=1)
                
                # Create mono filename
                base, ext = os.path.splitext(audio_path)
                mono_path = f"{base}_mono.wav"
                
                # Save mono file
                sf.write(mono_path, mono_signal, sample_rate)
                print(f"✅ Mono version saved: {mono_path}")
                
                return mono_path
            else:
                print(f"✅ Audio is already mono: {os.path.basename(audio_path)}")
                return audio_path
                
        except Exception as e:
            print(f"❌ Error converting to mono: {e}")
            return audio_path
    
    def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file to text with timestamps.
        
        Args:
            audio_path: Path to the audio file to transcribe
            
        Returns:
            Dictionary containing transcription results and metadata
        """
        if not self.is_ready():
            raise Exception("ASR model is not loaded")
        
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        try:
            print(f"🎤 Starting transcription: {os.path.basename(audio_path)}")
            
            # Ensure audio is mono
            mono_audio_path = self.ensure_mono_audio(audio_path)
            
            # Transcribe with timestamps
            print("🔍 Transcribing audio...")
            output = self.model.transcribe([mono_audio_path], return_hypotheses=True)
            
            if not output or not isinstance(output, list):
                raise Exception("Transcription failed - no output received")
            
            # Extract transcription results
            result = output[0]
            
            # Get the full transcript text
            full_text = result.text if hasattr(result, 'text') else ""
            
            # Extract timestamps
            word_timestamps = []
            segment_timestamps = []
            
            if hasattr(result, 'timestamp') and result.timestamp:
                # Word-level timestamps
                if 'word' in result.timestamp:
                    word_timestamps = result.timestamp['word']
                
                # Segment-level timestamps
                if 'segment' in result.timestamp:
                    segment_timestamps = result.timestamp['segment']
            
            # Clean up mono file if it was created
            if mono_audio_path != audio_path and os.path.exists(mono_audio_path):
                os.remove(mono_audio_path)
                print(f"🧹 Cleaned up mono file: {mono_audio_path}")
            
            print(f"✅ Transcription completed: {len(full_text)} characters")
            
            return {
                "full_text": full_text,
                "segments": segment_timestamps,
                "asr_confidence": 0.9,  # High confidence for NeMo
                "asr_metadata": {
                    "word_timestamps": word_timestamps,
                    "audio_duration": self._get_audio_duration(audio_path),
                    "model_used": self.model_name,
                    "device_used": self.device
                }
            }
            
        except Exception as e:
            print(f"❌ Transcription failed: {e}")
            traceback.print_exc()
            raise
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """Get the duration of an audio file in seconds."""
        try:
            signal, sample_rate = sf.read(audio_path)
            return len(signal) / sample_rate
        except:
            return 0.0
    
    def store_transcript(self, submission_id: str, transcript_data: Dict[str, Any]) -> str:
        """
        Store transcription results in the database.
        
        Args:
            submission_id: The video submission ID
            transcript_data: Transcription results from transcribe_audio()
            
        Returns:
            The transcript ID from the database
        """
        try:
            print(f"💾 Storing transcript for submission: {submission_id}")
            
            # Prepare transcript data for database storage
            transcript_json = {
                "full_text": transcript_data["full_text"],
                "word_timestamps": transcript_data["word_timestamps"],
                "segment_timestamps": transcript_data["segment_timestamps"],
                "audio_duration": transcript_data["audio_duration"],
                "model_used": transcript_data["model_used"],
                "device_used": transcript_data["device_used"]
            }
            
            # Insert into transcripts table
            query = """
            INSERT INTO transcripts (submission_id, text, segments, 
                                   asr_confidence, asr_metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING transcript_id
            """
            
            result = execute_query(
                query,
                (
                    submission_id,
                    transcript_data["full_text"],
                    json.dumps(transcript_data["segments"]),  # Convert list to JSON string
                    transcript_data["asr_confidence"],
                    json.dumps(transcript_data["asr_metadata"])  # Convert dict to JSON string
                ),
                fetch_one=True
            )
            
            transcript_id = result["transcript_id"]
            print(f"✅ Transcript stored with ID: {transcript_id}")
            
            return transcript_id
            
        except Exception as e:
            print(f"❌ Failed to store transcript: {e}")
            traceback.print_exc()
            raise
    
    def get_transcript(self, submission_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve transcript from database.
        
        Args:
            submission_id: The video submission ID
            
        Returns:
            Transcript data or None if not found
        """
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
                return {
                    "transcript_id": result["transcript_id"],
                    "full_text": result["text"],
                    "segments": json.loads(result["segments"]) if result["segments"] else [],
                    "asr_confidence": result["asr_confidence"],
                    "asr_metadata": json.loads(result["asr_metadata"]) if result["asr_metadata"] else {},
                    "created_at": result["created_at"]
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Failed to retrieve transcript: {e}")
            return None

# Global ASR service instance
asr_service = ASRService()
