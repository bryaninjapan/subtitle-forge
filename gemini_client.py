import os
import threading
import sys
from google import genai

_client_lock = threading.Lock()
_client_instance = None

def get_gemini_client():
    """Returns a thread-safe singleton Gemini client with startup validation."""
    global _client_instance
    
    if _client_instance is not None:
        return _client_instance
        
    with _client_lock:
        if _client_instance is None:
            # 1. Load API Key
            api_key = os.environ.get("GEMINI_API_KEY", "").strip()
            if not api_key:
                from pathlib import Path
                env_path = Path(".env")
                if env_path.exists():
                    for line in env_path.read_text().splitlines():
                        if line.startswith("GEMINI_API_KEY="):
                            api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
            
            if not api_key:
                print("\n[CRITICAL ERROR] GEMINI_API_KEY not found in environment or .env file.")
                sys.exit(1)

            # 2. Validation (Single-shot low cost call)
            try:
                test_client = genai.Client(api_key=api_key)
                _ = list(test_client.models.list(config={'page_size': 1}))
            except Exception as e:
                print(f"\n[CRITICAL ERROR] Gemini API Validation Failed: {e}")
                print("Check your API key and quota at https://aistudio.google.com/app/apikey")
                sys.exit(1)
                
            _client_instance = genai.Client(api_key=api_key)
            
    return _client_instance
