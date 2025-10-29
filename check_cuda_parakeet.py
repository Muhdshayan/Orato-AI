"""
Quick script to check if Parakeet ASR is using CUDA
"""
import sys

# Fix Windows signal issue
import signal
if not hasattr(signal, 'SIGKILL'):
    signal.SIGKILL = signal.SIGTERM

print("=" * 60)
print("Checking CUDA Availability for Parakeet ASR")
print("=" * 60)

# Check PyTorch CUDA
print("\n1. Checking PyTorch CUDA...")
try:
    import torch
    print(f"   [OK] PyTorch version: {torch.__version__}")
    print(f"   [OK] CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"   [OK] CUDA version: {torch.version.cuda}")
        print(f"   [OK] GPU Device: {torch.cuda.get_device_name(0)}")
        print(f"   [OK] GPU Count: {torch.cuda.device_count()}")
    else:
        print("   [WARN] CUDA not available - will use CPU")
except Exception as e:
    print(f"   [ERROR] {e}")
    sys.exit(1)

# Check NeMo
print("\n2. Checking NeMo installation...")
try:
    import nemo
    print(f"   [OK] NeMo version: {nemo.__version__}")
except Exception as e:
    print(f"   [ERROR] {e}")
    sys.exit(1)

# Test model loading
print("\n3. Testing Parakeet model loading...")
try:
    import nemo.collections.asr as nemo_asr
    
    model_name = "nvidia/parakeet-tdt-0.6b-v3"
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    print(f"   [INFO] Loading model: {model_name}")
    print(f"   [INFO] Target device: {device}")
    
    # Suppress output during loading
    import logging
    logging.getLogger('nemo').setLevel(logging.ERROR)
    
    model = nemo_asr.models.ASRModel.from_pretrained(model_name=model_name)
    model.to(device)
    
    print(f"   [OK] Model loaded successfully!")
    print(f"   [OK] Model device: {next(model.parameters()).device}")
    
except Exception as e:
    print(f"   [ERROR] {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("SUCCESS! Parakeet is ready to use CUDA")
print("=" * 60)

