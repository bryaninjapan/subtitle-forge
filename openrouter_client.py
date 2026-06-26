import os
import threading
import sys
from dotenv import load_dotenv

_client_lock = threading.Lock()
_client_instance = None

load_dotenv()

def get_openrouter_client():
    """Returns a thread-safe singleton OpenRouter client (OpenAI-compatible API)."""
    global _client_instance

    if _client_instance is not None:
        return _client_instance

    with _client_lock:
        if _client_instance is None:
            api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()

            if not api_key:
                print("\n[CRITICAL ERROR] OPENROUTER_API_KEY not found in environment or .env file.")
                print("Get a free key at https://openrouter.ai/keys")
                sys.exit(1)

            try:
                from openai import OpenAI
            except ImportError:
                print("\n[CRITICAL ERROR] 'openai' package not installed. Run: pip install openai")
                sys.exit(1)

            _client_instance = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
            )

    return _client_instance
