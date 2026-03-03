import os
import json
import gradio as gr
import nemo.collections.asr as nemo_asr
import spaces
import librosa
import numpy as np
import torch
from huggingface_hub import hf_hub_download

# 1. SETTINGS - Matches your public repo perfectly
REPO_ID = "Ali428/parakeet-weights"
FILENAME = "parakeet_final.nemo"

print(f"🚀 Initializing FYP ASR Engine...")

try:
    # 2. DOWNLOAD THE FILE (No token needed for public repos)
    print(f"Downloading {FILENAME} from {REPO_ID}...")
    model_path = hf_hub_download(
        repo_id=REPO_ID, 
        filename=FILENAME
    )
    
    # 3. LOAD THE NEMO MODEL
    print(f"Loading model into memory...")
    model = nemo_asr.models.ASRModel.restore_from(model_path)
    model.eval()
    print("✅ Model loaded successfully!")

except Exception as e:
    print(f"❌ ERROR DURING STARTUP: {e}")
    raise e

# 4. TRANSCRIPTION FUNCTION
@spaces.GPU(duration=120)  # Increased duration slightly for long videos
def transcribe(audio_path):
    if audio_path is None:
        return json.dumps({"success": False, "error": "Please upload an audio file."})
    
    try:
        # 1. Get audio duration using librosa
        audio, sr = librosa.load(audio_path, sr=16000, mono=True)
        duration = len(audio) / sr
        
        # 2. Transcribe with return_hypotheses=True to get timestamps
        transcription = model.transcribe([audio_path], return_hypotheses=True)
        
        # Extract the hypothesis object
        hypothesis = transcription[0][0] if isinstance(transcription[0], list) else transcription[0]
        full_text = hypothesis.text

        # DEBUG: log timestep info to diagnose CPU vs GPU timestamp differences
        _ts = getattr(hypothesis, 'timestep', None)
        print(f"DEBUG has_timestep={hasattr(hypothesis, 'timestep')} | type={type(_ts)} | len={len(_ts) if _ts is not None and hasattr(_ts, '__len__') else 'N/A'} | sample={_ts[:5] if _ts is not None and hasattr(_ts, '__len__') and len(_ts) > 0 else _ts}")
        print(f"DEBUG has_words={hasattr(hypothesis, 'words')} | device=cuda:{torch.cuda.is_available()}")

        
        # 3. Process timestamps
        segments = []
        try:
            timestep = getattr(hypothesis, 'timestep', None)
            words = getattr(hypothesis, 'words', None) or full_text.split()

            # DEBUG: log to HF Space logs so we can inspect CPU behaviour
            print(f"DEBUG timestep type={type(timestep)} | has_words={hasattr(hypothesis, 'words')} | cuda={torch.cuda.is_available()}")
            if timestep is not None:
                print(f"DEBUG timestep value (raw)={str(timestep)[:200]}")

            # NeMo may return timestep as a Tensor, list, dict, or None
            if timestep is None:
                raise ValueError("timestep is None — will use fallback")

            # If it's a dict (e.g. {'timestep': [...], 'word': [...]})
            if isinstance(timestep, dict):
                timestep = timestep.get('timestep') or timestep.get('word') or list(timestep.values())[0]

            # Convert to numpy array
            if isinstance(timestep, torch.Tensor):
                timestep_array = timestep.cpu().numpy()
            else:
                timestep_array = np.array(timestep, dtype=np.float32)

            if len(timestep_array) == 0:
                raise ValueError("timestep array is empty — will use fallback")

            # Parakeet TDT uses 8x encoder subsampling (4x conv + 2x additional)
            # so each encoder frame = 8 * 10ms = 80ms of real audio time
            frame_duration = 0.08
            words_per_segment = 15

            frames_per_word = len(timestep_array) / len(words)
            word_timestamps = []

            for i, word in enumerate(words):
                start_frame = int(i * frames_per_word)
                end_frame   = int((i + 1) * frames_per_word)
                start_frame = min(start_frame, len(timestep_array) - 1)
                end_frame   = min(end_frame,   len(timestep_array))

                if end_frame > start_frame:
                    actual_start_frame = int(timestep_array[start_frame])
                    actual_end_frame   = int(timestep_array[min(end_frame - 1, len(timestep_array) - 1)])
                else:
                    actual_start_frame = int(timestep_array[start_frame])
                    actual_end_frame   = actual_start_frame

                word_timestamps.append({
                    'word':  word,
                    'start': round(actual_start_frame * frame_duration, 3),
                    'end':   round(actual_end_frame   * frame_duration, 3),
                })

            # Group into segments of words_per_segment words each
            for i in range(0, len(word_timestamps), words_per_segment):
                seg = word_timestamps[i:i + words_per_segment]
                if seg:
                    segments.append({
                        'text':  ' '.join(w['word'] for w in seg),
                        'start': seg[0]['start'],
                        'end':   seg[-1]['end'],
                    })


        except Exception as e:
            print(f"Warning: Timestamp extraction failed: {e}")
            # Fallback segments method
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

        # 4. Construct response identical to local backend
        word_count = len(full_text.split())

        result = {
            "success": True,
            "text": full_text,
            "segment_timestamps": segments,
            "model": "nvidia/parakeet-tdt-0.6b-v3",
            "device": "cuda" if torch.cuda.is_available() else "cpu",
            "audio_duration": round(duration, 2),
            "word_count": word_count,
            # DEBUG: remove once timestamps are confirmed working
            "debug_info": {
                "has_timestep": hasattr(hypothesis, 'timestep'),
                "timestep_type": str(type(getattr(hypothesis, 'timestep', None))),
                "timestep_len": len(getattr(hypothesis, 'timestep', [])) if hasattr(hypothesis, 'timestep') else 0,
                "timestep_sample": str(getattr(hypothesis, 'timestep', None))[:100] if hasattr(hypothesis, 'timestep') else None,
                "has_words": hasattr(hypothesis, 'words'),
                "cuda_available": torch.cuda.is_available(),
                "segments_from_fallback": len(segments) > 0 and segments[-1]['end'] > 190,
            }
        }

        
        # Return as pretty JSON string for the Gradio UI
        return json.dumps(result, indent=2)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)

# 5. GRADIO INTERFACE
# For API usage, we can skip the UI, but we'll leave it for debugging
demo = gr.Interface(
    fn=transcribe,
    inputs=gr.Audio(type="filepath", label="Upload Audio"),
    outputs=gr.Code(language="json", label="Transcription Result JSON"), # Changed to Code/JSON for better formatting
    title="Ali's FYP: Parakeet ASR Engine",
    description="Running on NVIDIA A100 (ZeroGPU). API-ready endpoint.",
    api_name="transcribe" # Allows api requests to /api/transcribe
)

if __name__ == "__main__":
    demo.launch()
