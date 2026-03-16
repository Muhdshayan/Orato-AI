"""
Client to connect to Parakeet Model Server for transcription.
Falls back to subprocess approach if server is not available.
"""
import os
import sys
import json
import socket
import subprocess
import time
import traceback
import requests
from typing import Dict, Any


class ParakeetClient:
    """Client for communicating with Parakeet model server"""
    
    def __init__(self):
        # Get project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Server connection details
        if sys.platform == 'win32':
            self.server_host = '127.0.0.1'
            self.server_port = 8765
            self.use_tcp = True
        else:
            self.socket_path = os.path.join(project_root, '.cache', 'parakeet_server.sock')
            self.use_tcp = False
        
        # Fallback script path (for when server is not available)
        services_dir = os.path.dirname(__file__)
        self.project_root = project_root
        venv_path = os.path.join(project_root, 'venv_asr')

        # --- CHANGE STARTS HERE ---
        # Dynamic path selection for Windows vs Linux/Mac
        if sys.platform == 'win32':
            self.python_exe = os.path.join(venv_path, 'Scripts', 'python.exe')
        else:
            self.python_exe = os.path.join(venv_path, 'bin', 'python')
        # --- CHANGE ENDS HERE ---

        self.script_path = os.path.join(services_dir, 'transcribe_with_parakeet.py')
        
        # Cache for server availability check
        self._server_available = None
        self._last_check = 0
    
    def _check_server_available(self, timeout: float = 0.5) -> bool:
        """Check if model server is available"""
        current_time = time.time()
        # Cache the check for 5 seconds
        if self._server_available is not None and (current_time - self._last_check) < 5:
            return self._server_available
        
        self._last_check = current_time
        
        try:
            if self.use_tcp:
                # TCP socket (Windows)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((self.server_host, self.server_port))
                sock.close()
                self._server_available = (result == 0)
            else:
                # Unix domain socket
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex(self.socket_path)
                sock.close()
                self._server_available = (result == 0)
            
            return self._server_available
        except Exception:
            self._server_available = False
            return False
    
    def _transcribe_via_modal(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe using the Modal GPU API (Tier 1)"""
        print(f"🚀 [Tier 1: Modal API] Attempting transcription for {os.path.basename(audio_path)}")
        url = "https://ali0346--orato-ai-parakeet-asr-api-transcribe.modal.run"
        
        with open(audio_path, 'rb') as f:
            files = {'file': (os.path.basename(audio_path), f, 'audio/wav')}
            # Use a long timeout to account for cold starts (e.g. 5 mins)
            response = requests.post(url, files=files, timeout=300)
            
        response.raise_for_status()
        result = response.json()
        
        if not result.get('success'):
            raise Exception(result.get('error', 'Unknown error from Modal API'))
            
        print(f"✅ [Tier 1: Modal API] Transcription successful")
        result['tier_used'] = 'Modal API (Cloud GPU)'
        return result

    def _transcribe_via_hf(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe using the HuggingFace Space API (Tier 2)"""
        from gradio_client import Client, file
        print(f"🚀 [Tier 2: HF API] Attempting transcription for {os.path.basename(audio_path)}")
        space_id = "Ali428/ParakeetTranscriptionModel"
        
        client = Client(space_id)
        # The HF API returns a JSON string, we need to parse it
        result_str = client.predict(
            audio_path=file(audio_path),
            api_name="/transcribe"
        )
        
        result = json.loads(result_str)
        
        if not result.get('success'):
            raise Exception(result.get('error', 'Unknown error from HF API'))
            
        print(f"✅ [Tier 2: HF API] Transcription successful")
        result['tier_used'] = 'HuggingFace API (Cloud CPU)'
        return result

    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio using a 3-tier fallback strategy:
        1. Modal API (Dedicated GPU, precise timestamps)
        2. HuggingFace API (CPU/ZeroGPU fallback)
        3. Local Model (Local GPU/CPU)
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Transcription result dictionary
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        print("\n" + "="*50)
        print(f"🎙️ STARTING ASR: {os.path.basename(audio_path)}")
        
        # TIER 1: Try Modal API (Fastest, best timestamps)
        try:
            return self._transcribe_via_modal(audio_path)
        except Exception as e:
            print(f"⚠️ [Modal API] Failed: {e}. Falling back to Tier 2 (HuggingFace API)...")
            
        # TIER 2: Try HuggingFace API (Secondary Cloud Fallback)
        try:
            return self._transcribe_via_hf(audio_path)
        except Exception as e:
            print(f"⚠️ [HF API] Failed: {e}. Falling back to Tier 3 (Local Model)...")

        # TIER 3: Local Model Server
        print(f"🚀 [Tier 3: Local Model] Attempting transcription via local model server")
        if self._check_server_available():
            try:
                result = self._transcribe_via_server(audio_path)
                print(f"✅ [Tier 3: Local Server] Transcription successful")
                result['tier_used'] = 'Local Server'
                return result
            except Exception as e:
                print(f"⚠️ [Local Server] Failed: {e}. Falling back to Local Subprocess...")
        
        # TIER 4: Local Subprocess (Final fallback)
        print(f"🚀 [Tier 3: Local Subprocess] Attempting raw subprocess transcription")
        result = self._transcribe_via_subprocess(audio_path)
        print(f"✅ [Tier 3: Local Subprocess] Transcription successful")
        result['tier_used'] = 'Local Subprocess'
        print("="*50 + "\n")
        return result
    
    def _transcribe_via_server(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe using model server via socket"""
        try:
            if self.use_tcp:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.server_host, self.server_port))
            else:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(self.socket_path)
            
            # Send request
            request = {
                'audio_path': audio_path
            }
            request_json = json.dumps(request) + '\n\n'
            sock.sendall(request_json.encode('utf-8'))
            
            # Receive response
            data = b''
            sock.settimeout(900)  # 15 minute timeout
            
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b'\n\n' in data:  # End of response marker
                    break
            
            sock.close()
            
            # Parse response
            response = json.loads(data.decode('utf-8').strip())
            
            if not response.get('success'):
                raise Exception(response.get('error', 'Unknown error from model server'))
            
            return response
            
        except Exception as e:
            raise Exception(f"Model server communication failed: {e}")
    
    def _transcribe_via_subprocess(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe using subprocess (original method, loads model each time)"""
        try:
            if not os.path.exists(self.python_exe):
                raise Exception(f"Python executable not found: {self.python_exe}")
            if not os.path.exists(self.script_path):
                raise Exception(f"Transcription script not found: {self.script_path}")
            
            # Call Parakeet script
            cmd = [self.python_exe, self.script_path, audio_path]
            
            env = os.environ.copy()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=900,
                env=env
            )
            
            if result.returncode != 0:
                error_msg = f"Parakeet script failed with return code {result.returncode}"
                if result.stderr:
                    error_msg += f"\nStderr:\n{result.stderr}"
                if result.stdout:
                    error_msg += f"\nStdout:\n{result.stdout}"
                raise Exception(error_msg)
            
            # Parse JSON output
            stdout_lines = result.stdout.strip().split('\n')
            json_str = None
            for line in reversed(stdout_lines):
                line = line.strip()
                if line.startswith('{') and line.endswith('}'):
                    json_str = line
                    break
            
            if json_str is None:
                json_str = result.stdout
            
            data = json.loads(json_str)
            
            if not data.get('success'):
                error_msg = data.get('error', 'Unknown error')
                raise Exception(f"Parakeet transcription failed: {error_msg}")
            
            return data
            
        except Exception as e:
            raise Exception(f"Subprocess transcription failed: {e}")


# Global client instance
parakeet_client = ParakeetClient()

