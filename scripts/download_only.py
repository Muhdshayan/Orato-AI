import os
import shutil
from huggingface_hub import hf_hub_download

# 1. Point to your local cache folder where the data is
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
hf_cache = os.path.join(project_root, '.cache', 'huggingface')
os.environ['HF_HOME'] = hf_cache

print(f"Downloading model to {hf_cache}...")
print("This will resume the download if it was partially completed.")

try:
    # This ONLY downloads the model file (or resumes the download) without loading it
    cached_file_path = hf_hub_download(
        repo_id="nvidia/parakeet-tdt-0.6b-v3",
        filename="parakeet-tdt-0.6b-v3.nemo",
        cache_dir=hf_cache
    )
    
    # 2. This creates the SINGLE 2.5GB file you need
    output_path = os.path.join(project_root, "parakeet_final.nemo")
    
    print(f"Download complete! Copying the model to {output_path}...")
    shutil.copy2(cached_file_path, output_path)
    
    print(f"\n✅ SUCCESS! Your model is now saved as: {os.path.abspath(output_path)}")
    print("This is the ONLY file you need to upload to Hugging Face.")

except Exception as e:
    print(f"\n❌ Error: {e}")
