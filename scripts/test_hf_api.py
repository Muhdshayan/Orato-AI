import json
import os
import time
from gradio_client import Client, handle_file

HF_SPACE = "Ali428/ParakeetTranscriptionModel"

def test_hf_api(audio_path):
    print(f"🎤 Testing HuggingFace API with: {os.path.basename(audio_path)}")
    print(f"🌐 Space: https://huggingface.co/spaces/{HF_SPACE}")
    print("⏳ Waiting for transcription (may take a moment if the Space is sleeping)...")

    client = Client(HF_SPACE)

    t_start = time.time()
    result = client.predict(
        audio_path=handle_file(audio_path),
        api_name="/transcribe",
    )
    elapsed = time.time() - t_start

    print(f"\n⏱️  Total call time : {elapsed:.2f}s  ({elapsed/60:.1f} min)")
    print("\n─── RAW RESPONSE ────────────────────────────────────────────────────")

    # The API returns a JSON string — try to pretty-print it
    try:
        parsed = json.loads(result)
        print(json.dumps(parsed, indent=2))
    except (json.JSONDecodeError, TypeError):
        # If it's not JSON, just print it as-is
        print(result)

    print("─────────────────────────────────────────────────────────────────────")


if __name__ == "__main__":
    test_audio = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "Spoken English Presentation Class at Yashal English House.wav"
    )

    if os.path.exists(test_audio):
        test_hf_api(test_audio)
    else:
        print(f"⚠️  Test audio file not found at: {test_audio}")
