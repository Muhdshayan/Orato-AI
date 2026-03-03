import os
import sys

def download_model():
    # Setup exactly the same environment layout as the server
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hf_cache = os.path.join(project_root, '.cache', 'huggingface')
    temp_dir = os.path.join(project_root, '.cache', 'temp')
    nemo_cache = os.path.join(project_root, '.cache', 'nemo_models')
    
    os.makedirs(hf_cache, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(nemo_cache, exist_ok=True)
    
    # Configure NeMo and HF to use the project local directories
    os.environ['HF_HOME'] = hf_cache
    os.environ['HUGGINGFACE_HUB_CACHE'] = hf_cache
    os.environ['TMPDIR'] = temp_dir
    os.environ['TEMP'] = temp_dir
    os.environ['TMP'] = temp_dir
    os.environ['NEMO_CACHE_DIR'] = nemo_cache
    os.environ['NEMO_EXTRACTION_DIR'] = nemo_cache
    
    # FORCE ONLINE MODE (unlike the server which uses offline mode)
    os.environ['TRANSFORMERS_OFFLINE'] = '0'
    os.environ['HF_HUB_OFFLINE'] = '0'
    
    print(f"Downloading Parakeet model (nvidia/parakeet-tdt-0.6b-v3)...")
    print(f"Target directory: {hf_cache}")
    
    try:
        import torch
        import nemo.collections.asr as nemo_asr
        
        # This triggers the automatic download from HuggingFace
        model = nemo_asr.models.ASRModel.from_pretrained(model_name="nvidia/parakeet-tdt-0.6b-v3")
        print("\n✅ Download complete! The model is now cached and ready for offline use.")
        
    except Exception as e:
        print(f"\n❌ Error downloading model: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    download_model()
