"""
Phase-5 — AI Handler (backward-compatible)
Wraps the Ollama offline model. Kept for backward compatibility.
New code should use core.hybrid_handler.HybridAIHandler instead.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

import requests  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen2.5:1.5b"


class AIHandler:
    """Sends prompts to a locally-running Ollama instance and returns the
    full response text.

    Parameters
    ----------
    model : str
        Name of the Ollama model to use.
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

    def generate_response(
        self,
        prompt: str,
        context: Optional[str] = None,
    ) -> str:
        """Send *prompt* to Ollama and return the generated text."""
        system_prompt = self._build_system_prompt(context)

        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "num_ctx": 2048,
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
            msg = f"⚠️ Ollama returned an error: {exc}"
            logger.error(msg)
            return msg

        except Exception as exc:  # noqa: BLE001
            msg = f"⚠️ Unexpected error: {exc}"
            logger.exception(msg)
            return msg

    @staticmethod
    def _build_system_prompt(context: Optional[str] = None) -> str:
        """Compose the system prompt sent to the model."""
        from datetime import datetime

        now = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        parts: list[str] = [
            f"You are Phase-5, a helpful offline AI personal assistant. "
            f"Today's date is {now}. "
            f"Always give complete answers. Never leave a sentence unfinished. "
            f"Be concise and accurate. You run fully offline on the user's PC. "
            f"If you are unsure or your knowledge may be outdated, say so honestly "
            f"instead of guessing.",
        ]
        if context:
            parts.append(f"Context:\n{context}")
        return "\n\n".join(parts)

    @staticmethod
    def _read_stream(response: requests.Response) -> str:
        """Read a streaming Ollama response (newline-delimited JSON)."""
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
