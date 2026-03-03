import requests
import json
import os
import time

MODAL_API_URL = "https://ali0346--orato-ai-parakeet-asr-api-transcribe.modal.run"

def test_api(audio_path):
    print(f"🎤 Testing Modal API with: {os.path.basename(audio_path)}")
    print(f"🌐 Sending request to: {MODAL_API_URL}")
    print("⏳ Waiting for transcription (this may take a moment if the GPU container needs to wake up)...")

    try:
        with open(audio_path, "rb") as f:
            audio_data = f.read()

        files = {"file": ("audio.wav", audio_data, "audio/wav")}

        t_start = time.time()
        response = requests.post(MODAL_API_URL, files=files, timeout=300)
        elapsed = time.time() - t_start

        print(f"\n⏱️  Total call time : {elapsed:.2f}s  ({elapsed/60:.1f} min)")
        print(f"📦 HTTP status     : {response.status_code}")
        print("\n─── RAW JSON RESPONSE ───────────────────────────────────────────────")
        print(json.dumps(response.json(), indent=2))
        print("─────────────────────────────────────────────────────────────────────")

    except Exception as e:
        print(f"\n❌ Request failed: {e}")

if __name__ == "__main__":
    test_audio = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "Spoken English Presentation Class at Yashal English House.wav"
    )

    if os.path.exists(test_audio):
        test_api(test_audio)
    else:
        print(f"⚠️ Test audio file not found at: {test_audio}")
