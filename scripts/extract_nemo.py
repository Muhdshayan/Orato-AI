import os
import nemo.collections.asr as nemo_asr

# 1. Point to your local cache folder where the data is
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ['HF_HOME'] = os.path.join(project_root, '.cache', 'huggingface')
os.environ['TMPDIR'] = os.path.join(project_root, '.cache', 'temp')
os.environ['TEMP'] = os.path.join(project_root, '.cache', 'temp')
os.environ['TMP'] = os.path.join(project_root, '.cache', 'temp')

print("Searching cache and packing model...")

try:
    # This will load the model from your ALREADY downloaded .cache folder
    model = nemo_asr.models.ASRModel.from_pretrained(model_name="nvidia/parakeet-tdt-0.6b-v3")
    
    # 2. This creates the SINGLE 2.5GB file you need
    output_path = os.path.join(project_root, "parakeet_final.nemo")
    model.save_to(output_path)
    
    print(f"\n✅ SUCCESS! Your model is now saved as: {os.path.abspath(output_path)}")
    print("This is the ONLY file you need to upload to Hugging Face.")

except Exception as e:
    print(f"\n❌ Error: {e}")
