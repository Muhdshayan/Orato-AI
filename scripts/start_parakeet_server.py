"""
Manual script to start the Parakeet model server.
This server keeps the model loaded in memory for fast transcription.
"""
import sys
import os

# Add backend to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_path = os.path.join(project_root, 'backend')
sys.path.insert(0, backend_path)

from app.services.parakeet_model_server import start_model_server

if __name__ == '__main__':
    print("Starting Parakeet Model Server...")
    print("Press Ctrl+C to stop")
    start_model_server()

