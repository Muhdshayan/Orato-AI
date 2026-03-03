import os
import json
import modal

# 1. Define the Modal App
app = modal.App("orato-ai-parakeet-asr")

# Get absolute path to the local model relative to this script
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
model_local_path = os.path.join(project_root, "ParakeetNemo", "parakeet_final.nemo")

# 2. Define the container environment and copy the local model file directly into the image
image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("ffmpeg", "libsndfile1")
    # Install CUDA-enabled PyTorch 2.2.2 FIRST (before anything else)
    .pip_install(
        "torch==2.2.2",
        "torchaudio==2.2.2",
        extra_index_url="https://download.pytorch.org/whl/cu121"
    )
    # Pin numpy<2: torch==2.2.2 was compiled against NumPy 1.x ABI — NumPy 2.x breaks it
    # Pin transformers==4.44.0: transformers 5.x requires torch>=2.4, but we have 2.2.2
    # Add matplotlib: nemo.collections.asr imports it on startup via clustering_diarizer
    .pip_install(
        "numpy<2",
        "transformers==4.44.0",
        "matplotlib",
    )
    # Now install NeMo with the correct pinned dependencies already in place
    .pip_install(
        "nemo_toolkit[asr]==2.0.0",
        "librosa",
        "soundfile",
        "fastapi[standard]",
        "python-multipart",
    )
    # CRITICAL: Force numpy back to 1.26.4 AFTER nemo install.
    # nemo_toolkit re-upgrades numpy to 2.x during its install, which breaks
    # NeMo's own segment.py which uses np.sctypes (removed in NumPy 2.0).
    .pip_install("numpy==1.26.4")
    # Bake the local model directly into the remote container
    .add_local_file(local_path=model_local_path, remote_path="/root/parakeet_final.nemo")
)

# 4. Define the GPU-powered class
@app.cls(
    image=image,
    gpu="A10G",
    scaledown_window=60,
    timeout=600,  # 10 minutes for cold start (loading model into VRAM)
)
class ParakeetEngine:
    @modal.enter()
    def setup(self):
        """Loads the model into VRAM when the container starts."""
        import nemo.collections.asr as nemo_asr
        from omegaconf import open_dict
        
        print("Loading model into VRAM from baked path /root/parakeet_final.nemo...")
        self.model = nemo_asr.models.ASRModel.restore_from("/root/parakeet_final.nemo")
        self.model.eval()
        
        # CRITICAL FIX: Disable CUDA Graphs to fix "not enough values to unpack (expected 6, got 5)".
        # NeMo 2.0.0's TDT decoder tries to compile CUDA Graphs, but Modal's A10G CUDA driver
        # returns 5 values from cu_call() while NeMo expects 6 — a version mismatch.
        # Disabling CUDA Graphs forces NeMo to use standard PyTorch ops, which work on any driver.
        print("Disabling CUDA Graphs for TDT decoding (CUDA driver compatibility fix)...")
        try:
            with open_dict(self.model.cfg):
                self.model.cfg.decoding.greedy.use_cuda_graph = False
            self.model.change_decoding_strategy(self.model.cfg.decoding)
            print("✅ CUDA Graphs disabled successfully.")
        except Exception as e:
            print(f"⚠️ Could not disable CUDA Graphs via config: {e}. Trying direct attribute patch...")
            try:
                # Fallback: directly patch the decoding object
                for attr in ['decoding_computer', '_decoding_computer']:
                    if hasattr(self.model.decoding, attr):
                        obj = getattr(self.model.decoding, attr)
                        if hasattr(obj, 'use_cuda_graph'):
                            obj.use_cuda_graph = False
                print("✅ CUDA Graphs disabled via direct patch.")
            except Exception as e2:
                print(f"⚠️ Direct patch also failed: {e2}. Proceeding anyway.")
        
        self.model.cuda()  # Move to GPU
        print("✅ Model loaded and ready for transcription!")

    @modal.method()
    def transcribe(self, audio_bytes: bytes) -> dict:
        """The core transcription logic mapping exactly to your backend's expected JSON."""
        import librosa
        import numpy as np
        import tempfile
        import torch
        
        # Save initial raw bytes to a temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_raw:
            tmp_raw.write(audio_bytes)
            tmp_raw.flush()
            raw_path = tmp_raw.name
            
        normalized_path = raw_path + "_normalized.wav"
        
        try:
            # 1. Load and normalize audio (16kHz, mono)
            import soundfile as sf
            audio, sr = librosa.load(raw_path, sr=16000, mono=True)
            duration = len(audio) / sr
            
            # Write out normalized pure WAV file for NeMo dataloader
            sf.write(normalized_path, audio, sr)
            
            # 2. Transcribe using the NORMALIZED audio file
            # Restored return_hypotheses=True since the unpack error was caused by bad audio formats
            transcriptions = self.model.transcribe([normalized_path], return_hypotheses=True)
            
            # Safely unpack the single returned string/list
            if isinstance(transcriptions, tuple):
                transcriptions = transcriptions[0]
            
            full_text = transcriptions[0] if isinstance(transcriptions, list) else str(transcriptions)
            
            # 3. Process timestamps
            segments = []
            
            try:
                # Get true hypotheses attributes if available
                hypothesis = transcriptions[0] if isinstance(transcriptions, list) else transcriptions
                full_text = hypothesis.text if hasattr(hypothesis, 'text') else str(hypothesis)
                timestep = hypothesis.timestep if hasattr(hypothesis, 'timestep') else None
                words = hypothesis.words if hasattr(hypothesis, 'words') else full_text.split()
                
                if timestep is not None:
                    if isinstance(timestep, torch.Tensor):
                        timestep_array = timestep.cpu().numpy() if timestep.is_cuda else timestep.numpy()
                    else:
                        timestep_array = np.array(timestep)
                    
                    # Parakeet TDT uses 8x encoder subsampling (4x conv + 2x additional),
                    # so each encoder frame = 8 * 10ms = 80ms of real audio time
                    frame_duration = 0.08  # was 0.01 — that was wrong (raw frame, not encoder frame)

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
                        
                        # Group into segments
                        for i in range(0, len(word_timestamps), words_per_segment):
                            segment_words = word_timestamps[i:i + words_per_segment]
                            if segment_words:
                                segments.append({
                                    'text': ' '.join([w['word'] for w in segment_words]),
                                    'start': round(segment_words[0]['start'], 3),
                                    'end': round(segment_words[-1]['end'], 3)
                                })
                
                # If segment extraction failed or yielded empty result, trigger fallback manually
                if not segments:
                    raise ValueError("No segments produced from true hypotheses")
                    
            except Exception as e:
                print(f"Warning: True Timestamp extraction failed: {e}")
                import traceback
                traceback.print_exc()
                
                # Fallback
                full_text = transcriptions[0] if isinstance(transcriptions, list) else str(transcriptions)
                segments = []
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

            # 4. Construct final payload
            word_count = len(full_text.split())
            return {
                "success": True,
                "text": full_text,
                "segment_timestamps": segments,
                "model": "nvidia/parakeet-tdt-0.6b-v3",
                "device": "cuda",
                "audio_duration": round(duration, 2),
                "word_count": word_count
            }
            
        finally:
            if os.path.exists(raw_path):
                os.remove(raw_path)
            if os.path.exists(normalized_path):
                os.remove(normalized_path)


from fastapi import UploadFile

# 5. Define the web endpoint (API)
@app.function(image=image, timeout=600)  # 10 minute timeout for cold starts
@modal.fastapi_endpoint(method="POST", docs=True)
async def api_transcribe(file: UploadFile):
    """
    Exposes a REST API. Send audio file as a form-data payload:
    curl -X POST -F "file=@audio.wav" https://ali0346--orato-ai-parakeet-asr-api-transcribe.modal.run
    """
    engine = ParakeetEngine()
    
    try:
        # Read the uploaded file into raw bytes
        audio_bytes = await file.read()
        
        # Call the GPU class
        result = engine.transcribe.remote(audio_bytes)
        return result
    except Exception as e:
        import traceback
        return {
            "success": False, 
            "error": str(e),
            "traceback": traceback.format_exc()
        }
