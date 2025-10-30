"""
Standalone script to transcribe audio using NeMo Parakeet ASR.
This runs in Python 3.10 environment with NeMo installed.
"""
import sys
import json
import os
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')

# Fix Windows signal issue
import signal
if not hasattr(signal, 'SIGKILL'):
    signal.SIGKILL = signal.SIGTERM

def cleanup_old_temp_files(temp_dir: str, max_age_hours: int = 24):
    """Clean up old temporary files and directories"""
    try:
        import time
        import shutil
        
        if not os.path.exists(temp_dir):
            return
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for item in os.listdir(temp_dir):
            item_path = os.path.join(temp_dir, item)
            try:
                # Get file/folder age
                item_age = current_time - os.path.getmtime(item_path)
                
                # Remove if older than max_age
                if item_age > max_age_seconds:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path, ignore_errors=True)
                        print(f"Cleaned up old temp directory: {item}", file=sys.stderr)
                    else:
                        os.remove(item_path)
                        print(f"Cleaned up old temp file: {item}", file=sys.stderr)
            except Exception as e:
                # Ignore errors (file might be in use)
                pass
    except Exception as e:
        print(f"Warning: Temp cleanup failed: {e}", file=sys.stderr)

def transcribe_audio(audio_path: str):
    """Transcribe audio file using NeMo Parakeet"""
    try:
        # Set HuggingFace cache to project directory (models will be stored here)
        # File is in backend/app/services/, so go up 4 levels to project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        hf_cache = os.path.join(project_root, '.cache', 'huggingface')
        temp_dir = os.path.join(project_root, '.cache', 'temp')
        
        # Clean up old temp files (older than 24 hours)
        cleanup_old_temp_files(temp_dir, max_age_hours=24)
        
        # Create directories if they don't exist
        os.makedirs(hf_cache, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)
        
        # Set HuggingFace cache location (D: drive)
        os.environ['HF_HOME'] = hf_cache
        os.environ['HUGGINGFACE_HUB_CACHE'] = hf_cache
        
        # Force temp/download directory to D: drive (prevents C: drive usage)
        os.environ['TMPDIR'] = temp_dir
        os.environ['TEMP'] = temp_dir
        os.environ['TMP'] = temp_dir
        
        # Set fixed NeMo model extraction directory (reuse extracted model, don't re-extract)
        nemo_cache = os.path.join(project_root, '.cache', 'nemo_models')
        os.makedirs(nemo_cache, exist_ok=True)
        os.environ['NEMO_CACHE_DIR'] = nemo_cache
        os.environ['NEMO_EXTRACTION_DIR'] = nemo_cache
        
        print(f"Using NeMo cache directory: {nemo_cache}", file=sys.stderr)
        
        # Set environment variables for Windows compatibility
        os.environ['HYDRA_FULL_ERROR'] = '0'
        os.environ['OMP_NUM_THREADS'] = '1'
        
        # Suppress NeMo logging to stdout (only JSON should go to stdout)
        os.environ['NEMO_LOG_LEVEL'] = 'ERROR'
        
        # Configure logging BEFORE importing NeMo to prevent stdout pollution
        import logging
        
        # Disable all NeMo logging by setting root logger and specific loggers
        logging.basicConfig(level=logging.ERROR, stream=sys.stderr)
        logging.getLogger().setLevel(logging.ERROR)
        
        # Create a custom handler that only writes to stderr
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setLevel(logging.ERROR)
        
        # Configure NeMo loggers BEFORE import
        for logger_name in ['nemo', 'pytorch_lightning', 'lightning', 'transformers', 'torch']:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.ERROR)
            logger.handlers = [stderr_handler]
            logger.propagate = False
        
        import torch
        import nemo.collections.asr as nemo_asr
        import librosa
        
        # Additional suppression after import
        for logger_name in ['nemo', 'pytorch_lightning', 'lightning']:
            logging.getLogger(logger_name).setLevel(logging.ERROR)
        
        # Load model
        model_name = "nvidia/parakeet-tdt-0.6b-v3"
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        print(f"Loading model: {model_name}", file=sys.stderr)
        
        # Temporarily replace stdout with stderr to prevent NeMo logs from polluting JSON output
        original_stdout = sys.stdout
        sys.stdout = sys.stderr
        
        try:
            model = nemo_asr.models.ASRModel.from_pretrained(model_name=model_name)
            model.to(device)
        finally:
            # Restore original stdout
            sys.stdout = original_stdout
        
        # Load audio to get duration (force mono for compatibility)
        audio, sr = librosa.load(audio_path, sr=16000, mono=True)
        duration = len(audio) / sr
        
        # Save as temporary mono WAV file for NeMo (which expects mono audio)
        # Use a dedicated temp directory for this transcription session
        import tempfile
        import soundfile as sf
        import uuid
        
        # Create a unique temp subdirectory for this transcription
        session_temp_dir = os.path.join(temp_dir, f"transcribe_{uuid.uuid4().hex[:8]}")
        os.makedirs(session_temp_dir, exist_ok=True)
        
        mono_audio_path = os.path.join(session_temp_dir, "audio_mono.wav")
        sf.write(mono_audio_path, audio, sr)
        
        print(f"Audio converted to mono: {duration:.2f}s", file=sys.stderr)
        
        # Transcribe using mono audio file
        print(f"Transcribing audio...", file=sys.stderr)
        
        # Temporarily replace stdout with stderr during transcription
        sys.stdout = sys.stderr
        
        try:
            # Note: RNNT models don't support 'timestamps' parameter in transcribe()
            # We'll check what timestamp data is available in the hypothesis object
            transcription = model.transcribe(
                [mono_audio_path], 
                return_hypotheses=True
            )
        finally:
            # Restore original stdout
            sys.stdout = original_stdout
            
            # Clean up temporary session directory
            try:
                import shutil
                if os.path.exists(session_temp_dir):
                    shutil.rmtree(session_temp_dir, ignore_errors=True)
                    print(f"Cleaned up session temp directory", file=sys.stderr)
            except Exception as cleanup_error:
                print(f"Warning: Failed to cleanup temp directory: {cleanup_error}", file=sys.stderr)
        
        # Extract results
        hypothesis = transcription[0][0] if isinstance(transcription[0], list) else transcription[0]
        full_text = hypothesis.text
        
        print(f"Transcription completed: {len(full_text)} characters", file=sys.stderr)
        
        # Debug: Print hypothesis attributes to see what's available
        print(f"Hypothesis attributes: {dir(hypothesis)}", file=sys.stderr)
        
        # Extract segment timestamps from model output
        print(f"Extracting segment timestamps from model...", file=sys.stderr)
        segments = []
        
        try:
            import torch
            import numpy as np
            
            # Get timestep tensor and words
            timestep = hypothesis.timestep  # Frame indices for each token
            words = hypothesis.words if hasattr(hypothesis, 'words') else full_text.split()
            
            print(f"Timestep shape: {timestep.shape if hasattr(timestep, 'shape') else 'N/A'}", file=sys.stderr)
            print(f"Number of words: {len(words)}", file=sys.stderr)
            
            # Convert timestep tensor to numpy for easier processing
            if isinstance(timestep, torch.Tensor):
                timestep_array = timestep.cpu().numpy() if timestep.is_cuda else timestep.numpy()
            else:
                timestep_array = np.array(timestep)
            
            # Frame rate: NeMo models typically use 10ms frames (0.01s per frame)
            frame_duration = 0.01  # 10ms per frame
            
            # Create word-level timestamps from timestep data
            word_timestamps = []
            if len(timestep_array) > 0 and len(words) > 0:
                # Map frames to words (approximate alignment)
                frames_per_word = len(timestep_array) / len(words)
                
                for i, word in enumerate(words):
                    start_frame = int(i * frames_per_word)
                    end_frame = int((i + 1) * frames_per_word)
                    
                    # Ensure we don't exceed array bounds
                    start_frame = min(start_frame, len(timestep_array) - 1)
                    end_frame = min(end_frame, len(timestep_array))
                    
                    # Get actual frame indices from timestep array
                    if end_frame > start_frame:
                        actual_start_frame = int(timestep_array[start_frame])
                        actual_end_frame = int(timestep_array[min(end_frame - 1, len(timestep_array) - 1)])
                    else:
                        actual_start_frame = int(timestep_array[start_frame])
                        actual_end_frame = actual_start_frame
                    
                    # Convert frames to time
                    start_time = actual_start_frame * frame_duration
                    end_time = actual_end_frame * frame_duration
                    
                    word_timestamps.append({
                        'word': word,
                        'start': round(start_time, 3),
                        'end': round(end_time, 3)
                    })
            
            print(f"Created {len(word_timestamps)} word timestamps", file=sys.stderr)
            
            # Create segments by grouping words (e.g., 10-15 words per segment)
            words_per_segment = 15
            
            for i in range(0, len(word_timestamps), words_per_segment):
                segment_words = word_timestamps[i:i + words_per_segment]
                
                if segment_words:
                    segment_text = ' '.join([w['word'] for w in segment_words])
                    segment_start = segment_words[0]['start']
                    segment_end = segment_words[-1]['end']
                    
                    segments.append({
                        'text': segment_text,
                        'start': round(segment_start, 3),
                        'end': round(segment_end, 3)
                    })
            
            print(f"✓ Created {len(segments)} segments from word timestamps", file=sys.stderr)
                
        except Exception as e:
            print(f"Error extracting timestamps: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            
            # Fallback: create basic segments without timestamps
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
            
            print(f"✓ Created {len(segments)} fallback segments", file=sys.stderr)
        
        # ========== COMMENTED OUT: FAKE TIMESTAMP GENERATION ==========
        # # Perform forced alignment to get word-level timestamps
        # print(f"Performing forced alignment for word-level timestamps...", file=sys.stderr)
        # word_timestamps = []
        # 
        # try:
        #     from nemo.collections.asr.parts.utils.transcribe_utils import get_wer_feat
        #     import numpy as np
        #     
        #     # Split text into words
        #     words = full_text.split()
        #     
        #     # Calculate approximate word timings using audio energy
        #     # This is a simple heuristic-based alignment
        #     avg_word_duration = duration / max(1, len(words))
        #     
        #     # Use energy-based segmentation for better alignment
        #     frame_length = int(sr * 0.025)  # 25ms frames
        #     hop_length = int(sr * 0.010)    # 10ms hop
        #     
        #     # Calculate energy for each frame
        #     energy = []
        #     for i in range(0, len(audio) - frame_length, hop_length):
        #         frame = audio[i:i + frame_length]
        #         frame_energy = np.sum(frame ** 2)
        #         energy.append(frame_energy)
        #     
        #     energy = np.array(energy)
        #     threshold = np.mean(energy) * 0.3
        #     
        #     # Find speech segments (frames above threshold)
        #     speech_frames = energy > threshold
        #     
        #     # Distribute words across speech regions
        #     speech_regions = []
        #     in_speech = False
        #     start_frame = 0
        #     
        #     for i, is_speech in enumerate(speech_frames):
        #         if is_speech and not in_speech:
        #             start_frame = i
        #             in_speech = True
        #         elif not is_speech and in_speech:
        #             speech_regions.append((start_frame, i))
        #             in_speech = False
        #     
        #     if in_speech:
        #         speech_regions.append((start_frame, len(speech_frames)))
        #     
        #     # Distribute words across speech regions
        #     if speech_regions:
        #         words_per_region = len(words) / max(1, len(speech_regions))
        #         word_idx = 0
        #         
        #         for region_start, region_end in speech_regions:
        #             region_start_time = region_start * hop_length / sr
        #             region_end_time = region_end * hop_length / sr
        #             region_duration = region_end_time - region_start_time
        #             
        #             # How many words in this region?
        #             words_in_region = int(words_per_region)
        #             if word_idx + words_in_region > len(words):
        #                 words_in_region = len(words) - word_idx
        #             
        #             # Distribute words evenly in this region
        #             if words_in_region > 0:
        #                 word_duration = region_duration / words_in_region
        #                 for i in range(words_in_region):
        #                     if word_idx < len(words):
        #                         start_time = region_start_time + (i * word_duration)
        #                         end_time = start_time + word_duration
        #                         word_timestamps.append({
        #                             'word': words[word_idx],
        #                             'start_offset': round(start_time, 3),
        #                             'end_offset': round(end_time, 3)
        #                         })
        #                         word_idx += 1
        #     
        #     # Fallback: if no speech regions detected, use uniform distribution
        #     if not word_timestamps:
        #         for i, word in enumerate(words):
        #             start_time = i * avg_word_duration
        #             end_time = (i + 1) * avg_word_duration
        #             word_timestamps.append({
        #                 'word': word,
        #                 'start_offset': round(start_time, 3),
        #                 'end_offset': round(end_time, 3)
        #             })
        #     
        #     print(f"Extracted {len(word_timestamps)} word timestamps", file=sys.stderr)
        #     
        # except Exception as align_error:
        #     print(f"Forced alignment failed: {align_error}, using uniform distribution", file=sys.stderr)
        #     # Fallback to uniform distribution
        #     words = full_text.split()
        #     avg_word_duration = duration / max(1, len(words))
        #     for i, word in enumerate(words):
        #         start_time = i * avg_word_duration
        #         end_time = (i + 1) * avg_word_duration
        #         word_timestamps.append({
        #             'word': word,
        #             'start_offset': round(start_time, 3),
        #             'end_offset': round(end_time, 3)
        #         })
        # 
        # # Extract segments (create segments from text for compatibility)
        # segments = []
        # words = full_text.split()
        # words_per_segment = 10
        # segment_duration = duration / max(1, len(words) / words_per_segment)
        # 
        # for i in range(0, len(words), words_per_segment):
        #     segment_words = words[i:i+words_per_segment]
        #     segment_idx = i // words_per_segment
        #     segments.append({
        #         'label': ' '.join(segment_words),
        #         'start_offset': segment_idx * segment_duration,
        #         'end_offset': (segment_idx + 1) * segment_duration
        #     })
        # 
        # # Calculate pauses between words (for pause detection analysis)
        # pauses = []
        # for i in range(len(word_timestamps) - 1):
        #     current_word_end = word_timestamps[i]['end_offset']
        #     next_word_start = word_timestamps[i + 1]['start_offset']
        #     pause_duration = next_word_start - current_word_end
        #     
        #     # Only record significant pauses (> 0.3 seconds)
        #     if pause_duration > 0.3:
        #         pauses.append({
        #             'after_word': word_timestamps[i]['word'],
        #             'before_word': word_timestamps[i + 1]['word'],
        #             'duration': round(pause_duration, 3),
        #             'timestamp': round(current_word_end, 3)
        #         })
        # ========== END COMMENTED SECTION ==========
        
        # Count words
        word_count = len(full_text.split())
        
        # Return simplified JSON result with segment timestamps
        result = {
            'success': True,
            'text': full_text,
            'segment_timestamps': segments,
            'model': model_name,
            'device': device,
            'audio_duration': round(duration, 2),
            'word_count': word_count
        }
        
        print(json.dumps(result))
        return 0
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error details: {error_details}", file=sys.stderr)
        
        error_result = {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'text': '',
            'segment_timestamps': [],
            'model': 'nvidia/parakeet-tdt-0.6b-v3',
            'device': 'unknown',
            'audio_duration': 0,
            'word_count': 0
        }
        print(json.dumps(error_result))
        return 1

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(json.dumps({
            'success': False,
            'error': 'Usage: python transcribe_with_parakeet.py <audio_file>'
        }))
        sys.exit(1)
    
    audio_path = sys.argv[1]
    
    if not os.path.exists(audio_path):
        print(json.dumps({
            'success': False,
            'error': f'Audio file not found: {audio_path}'
        }))
        sys.exit(1)
    
    sys.exit(transcribe_audio(audio_path))

