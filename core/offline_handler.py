"""
Phase-5 — Offline AI Handler (Ollama)
Manages communication with the Ollama API running locally.
This is the fallback when internet is unavailable.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import threading
import time
from typing import Optional

import requests  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default configuration
# ---------------------------------------------------------------------------
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_OLLAMA_CHECK_URL = "http://localhost:11434/api/tags"
DEFAULT_MODEL = "qwen2.5:1.5b"  # fastest installed model — sub-10s on CPU


def _ensure_ollama_running() -> bool:
    """Check if Ollama is running and auto-start it if not.
    
    Returns True if Ollama is available, False if it's not installed.
    """
    # 1. Check if already running
    try:
        resp = requests.get(DEFAULT_OLLAMA_CHECK_URL, timeout=2)
        if resp.status_code == 200:
            return True
    except Exception:
        pass
    
    # 2. Try to find and launch ollama
    ollama_exe = shutil.which("ollama")
    if not ollama_exe:
        logger.error("Ollama is not installed — cannot start offline mode.")
        return False

    logger.info("Ollama not running. Auto-starting...")
    try:
        subprocess.Popen(
            [ollama_exe, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as exc:
        logger.error("Failed to start Ollama: %s", exc)
        return False

    # 3. Wait up to 8s for Ollama to become ready
    for _ in range(16):
        time.sleep(0.5)
        try:
            resp = requests.get(DEFAULT_OLLAMA_CHECK_URL, timeout=1)
            if resp.status_code == 200:
                logger.info("Ollama started successfully.")
                return True
        except Exception:
            continue

    logger.error("Ollama did not start in time.")
    return False


class OfflineHandler:
    """Sends prompts to a locally-running Ollama instance and returns the
    full response text.

    Parameters
    ----------
    model : str
        Name of the Ollama model to use (e.g. ``"qwen2.5:1.5b"``).
    base_url : str
        URL for the Ollama ``/api/generate`` endpoint.
    timeout : int
        Request timeout in seconds.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_OLLAMA_URL,
        timeout: int = 120,
    ) -> None:
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        # Pre-warm the model in a background thread so first real request is instant
        threading.Thread(target=self._warmup, daemon=True).start()

    def _warmup(self) -> None:
        """Send a dummy prompt to load the model into RAM before first real use."""
        try:
            if not _ensure_ollama_running():
                return
            import requests  # type: ignore[import-not-found]
            requests.post(
                self.base_url,
                json={
                    "model": self.model,
                    "prompt": "hi",
                    "stream": False,
                    "keep_alive": -1,
                    "options": {"num_predict": 1},
                },
                timeout=60,
            )
            logger.info("Offline model '%s' warmed up and ready.", self.model)
        except Exception:
            pass  # Warmup failure is non-fatal

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_response(
        self,
        prompt: str,
        context: Optional[str] = None,
    ) -> str:
        """Send *prompt* to Ollama and return the generated text.

        Parameters
        ----------
        prompt : str
            The user's message.
        context : str | None
            Optional context string (e.g. memory summary) that is prepended
            as a system-level instruction.

        Returns
        -------
        str
            The complete AI response, or a user-friendly error message.
        """
        system_prompt = self._build_system_prompt(context)

        # Auto-start Ollama if it's not running yet
        if not _ensure_ollama_running():
            return (
                "[OFFLINE] Ollama is not installed on this system. "
                "Please install it from https://ollama.com and run `ollama pull qwen2.5:1.5b`."
            )

        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "keep_alive": -1,           # KEY: keep model in RAM forever — no reload tax
            "options": {
                "num_ctx": 256,          # Minimal context = fastest possible generation
                "temperature": 0.3,     # Very focused, minimal computation
                "num_thread": 8,        # All CPU cores
                "num_predict": 180,     # Short sharp answers
                "repeat_penalty": 1.1,
                "num_keep": 4,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            response = requests.post(
                self.base_url,
                json=payload,
                timeout=self.timeout,
                stream=True,
            )
            response.raise_for_status()
            return self._read_stream(response)

        except requests.ConnectionError:
            msg = (
                "⚠️ Could not connect to Ollama. "
                "Make sure it is running (`ollama serve`)."
            )
            logger.error(msg)
            return msg

        except requests.Timeout:
            msg = (
                "⚠️ Response timed out — your system may be low on memory. "
                "Try closing other apps and asking again."
            )
            logger.error(msg)
            return msg

        except requests.HTTPError as exc:
            if exc.response.status_code == 404:
                msg = (
                    f"⚠️ **Model '{self.model}' not found.**\n\n"
                    f"Please run this command in your terminal:\n"
                    f"```\nollama pull {self.model}\n```"
                )
                logger.error("Ollama model not found: %s", self.model)
                return msg

            msg = f"⚠️ Ollama returned an error: {exc}"
            logger.error(msg)
            return msg

        except Exception as exc:  # noqa: BLE001
            msg = f"⚠️ Unexpected error: {exc}"
            logger.exception(msg)
            return msg

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_system_prompt(context: Optional[str] = None) -> str:
        """Compose the system prompt sent to the model."""
        from core.prompts import build_system_prompt  # type: ignore[import-not-found]
        return build_system_prompt(mode="offline", context=context)

    @staticmethod
    def _read_stream(response: requests.Response) -> str:
        """Read a streaming Ollama response (newline-delimited JSON)
        and concatenate all ``response`` fragments."""
        fragments: list[str] = []
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                data = json.loads(line)
                fragment = data.get("response", "")
                if fragment:
                    fragments.append(fragment)
                if data.get("done", False):
                    break
            except json.JSONDecodeError:
                continue
        return "".join(fragments) if fragments else "⚠️ Empty response from model."
