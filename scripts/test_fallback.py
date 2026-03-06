import os
import sys

# Add project root to sys.path so we can import python_modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from python_modules.nlp_asr.parakeet_client import parakeet_client

def override_urls_to_fail():
    """
    Temporarily patches the URLs inside the class methods 
    so Modal and HF will throw connection errors, forcing 
    the fallback to the 3rd tier (local python subprocess).
    """
    print("\n[TEST SETUP] Sabotaging cloud API endpoints to force local fallback...")
    
    # 1. Sabotage Modal URL
    original_modal = parakeet_client._transcribe_via_modal
    def broken_modal(audio_path):
        import requests
        print(f"[Modal API] Attempting transcription for {os.path.basename(audio_path)}", file=sys.stderr)
        # This domain does not exist, requests will throw an exception
        requests.post("https://this-url-definitely-does-not-exist.run", timeout=5)
    parakeet_client._transcribe_via_modal = broken_modal
    
    # 2. Sabotage HF Space
    original_hf = parakeet_client._transcribe_via_hf
    def broken_hf(audio_path):
        from gradio_client import Client
        print(f"[HF API] Attempting transcription for {os.path.basename(audio_path)}", file=sys.stderr)
        # Invalid Space ID
        Client("FakeUser12345/NonExistentSpace")
    parakeet_client._transcribe_via_hf = broken_hf


def test_fallback():
    # Use the 2-second audio file so your laptop doesn't freeze loading the 2.4GB model
    audio_file = os.path.join(project_root, 'test_short.wav')
    
    if not os.path.exists(audio_file):
        print(f"Test audio not found at: {audio_file}")
        return
        
    print(f"Testing parakeet_client 3-tier fallback on: {os.path.basename(audio_file)}")
    print("-" * 50)
    
    override_urls_to_fail()
    print("-" * 50)
    
    try:
        # 1. Tries Modal (Fails)
        # 2. Tries HF (Fails)
        # 3. Falls back to Local subprocess (Succeeds)
        result = parakeet_client.transcribe(audio_file)
        
        print("\n✅ Transcription Successful!")
        print(f"Model used: {result.get('model')}")
        print(f"Device used: {result.get('device')}")
        print(f"Duration: {result.get('audio_duration')}s")
        print(f"Words: {result.get('word_count')}")
        print(f"Extracted Text Snippet: {result.get('text', '')[:100]}...")
        print(f"Segment timestamps received: {len(result.get('segment_timestamps', []))}")
        
    except Exception as e:
        print(f"\n❌ Transcription Failed entirely: {e}")

if __name__ == "__main__":
    test_fallback()
