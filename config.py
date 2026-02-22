"""
Phase-5 — Configuration
Loads settings from .env and exposes them as module-level constants.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Load .env file (Robust Method — No Dependencies Required)
# ---------------------------------------------------------------------------
env_path = Path(__file__).parent / ".env"

def load_env_manual(path: Path) -> None:
    """Manually parse .env file if python-dotenv is missing."""
    if not path.exists():
        return
    
    try:
        content = path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            
            # Remove quotes if present
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]  # type: ignore[index]
                
            # Only set if not already in env (don't override system env vars)
            if key not in os.environ:
                os.environ[key] = value
    except Exception:
        pass

# Try python-dotenv first, fallback to manual
try:
    from dotenv import load_dotenv  # type: ignore[import-not-found]
    load_dotenv(env_path)
except ImportError:
    load_env_manual(env_path)

# ---------------------------------------------------------------------------
# Online (Groq) settings
# ---------------------------------------------------------------------------
ONLINE_API_KEY = os.getenv("ONLINE_API_KEY", "your-groq-api-key-here")
ONLINE_MODEL = os.getenv("ONLINE_MODEL", "llama-3.1-8b-instant")
ONLINE_BASE_URL: str = os.getenv(
    "ONLINE_BASE_URL",
    "https://api.groq.com/openai/v1/chat/completions",
)

# ---------------------------------------------------------------------------
# Offline (Ollama) settings
# ---------------------------------------------------------------------------
OFFLINE_MODEL: str = os.getenv("OFFLINE_MODEL", "qwen2.5:1.5b")
OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")


def is_online_configured() -> bool:
    """Return True if a valid-looking API key is present."""
    return bool(ONLINE_API_KEY) and ONLINE_API_KEY != "your-groq-api-key-here"
