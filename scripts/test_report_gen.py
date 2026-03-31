import asyncio
import os
import sys
import json
from unittest.mock import MagicMock, patch

# Ensure backend root is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.services.report_generator_service import ReportGeneratorService

async def test_report_logic():
    print("🚀 Initializing Report Generator Service Test...")
    
    # Mock data with various levels of performance
    mock_speech = {
        "fluency_score": 92.5,
        "speech_rate": 118.0,
        "filler_word_percentage": 2.1,
        "pause_count": 6
    }
    mock_visual = {
        "overall_score": 88.0,
        "individual_scores": {
            "eye_contact_score": 62.0,
            "cca_score": 45.0,
            "hand_visibility_score": 85.0
        },
        "gestures": {
            "gesture_frequency": {"gestures_per_minute": 12.5}
        }
    }
    mock_content = {
        "overall_score": 0.85 # Assuming it might be 0-1
    }

    # Instantiate service
    service = ReportGeneratorService()
    
    # Test 1: Scoring Logic (Synchronous)
    print("\n--- [Step 1] Scoring Logic Check ---")
    final_score = service._calculate_cumulative_score(mock_speech, mock_visual, mock_content)
    print(f"✅ Calculated Score: {final_score}")
    
    # Speech (35%) = 92.5 * 0.35 = 32.375
    # Visual (35%) = 88.0 * 0.35 = 30.8
    # Content (30%) = 85.0 * 0.30 = 25.5
    # Expected: 88.675 -> 88.68
    
    # Test 2: AI Feedback (Requires GROQ_API_KEY)
    print("\n--- [Step 2] AI Feedback Generation ---")
    if not os.getenv("GROQ_API_KEY") and not service.llm.groq_api_key:
        print("⚠️ Skipping AI test: GROQ_API_KEY environment variable not set.")
    else:
        try:
            feedback = await service._generate_ai_feedback(mock_speech, mock_visual, mock_content, final_score)
            print("✅ AI Feedback Received:")
            print(json.dumps(feedback, indent=4))
        except Exception as e:
            print(f"❌ AI Feedback Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_report_logic())
