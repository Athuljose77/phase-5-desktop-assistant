"""
Phase-5 — Online AI Handler
Sends prompts to a cloud LLM API (Groq / OpenAI-compatible) for high-quality
responses when the user has internet connectivity.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

import requests  # type: ignore[import-not-found]
try:
    from groq import Groq  # type: ignore[import-not-found, import]
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

logger = logging.getLogger(__name__)


class OnlineHandler:
    """Sends prompts to an OpenAI-compatible chat completions API (e.g. Groq).

    Parameters
    ----------
    api_key : str
        API key for authentication.
    model : str
        Model identifier (e.g. ``"llama-3.3-70b-versatile"``).
    base_url : str
        Full URL for the chat completions endpoint.
    timeout : int
        Request timeout in seconds.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.3-70b-versatile",
        base_url: str = "https://api.groq.com/openai/v1/chat/completions",
        timeout: int = 30,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        
        self.groq_client = None
        if GROQ_AVAILABLE and "groq" in base_url.lower():
            try:
                self.groq_client = Groq(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Groq client: {e}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_response(
        self,
        prompt: str,
        context: Optional[str] = None,
        image_path: Optional[str] = None,
    ) -> str:
        """Send *prompt* to the online LLM and return the response.

        Parameters
        ----------
        prompt : str
            The user's message.
        context : str | None
            Optional context / memory to include as system instructions.
        image_path : str | None
            Optional path to an image to analyze.

        Returns
        -------
        str
            The AI response, or a user-friendly error message.
        """
        import base64
        
        system_prompt = self._build_system_prompt(context)

        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        # Handle Vision
        if image_path:
            try:
                with open(image_path, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                })
            except Exception as e:
                logger.error(f"Failed to read image for vision: {e}")
                messages.append({"role": "user", "content": prompt}) # Fallback to text only
        else:
             messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Select model based on whether we have an image
        model_to_use = self.model
        if image_path and "groq" in self.base_url.lower():
            # Groq currently uses llama-3.2-90b-vision-preview or llama-3.2-11b-vision-preview for vision
            model_to_use = "llama-3.2-90b-vision-preview"

        # Use Groq SDK if available (much faster connection pooling than raw requests)
        if self.groq_client is not None:
            try:
                # The Groq SDK handles retries and connection properly
                chat_completion = self.groq_client.chat.completions.create(  # type: ignore
                    messages=messages, # type: ignore
                    model=model_to_use,
                    temperature=0.7,
                    max_completion_tokens=1024,
                    timeout=self.timeout
                )
                if chat_completion.choices:
                    return chat_completion.choices[0].message.content or "⚠️ Empty response."
                return "⚠️ No response from online model."
            except Exception as exc:
                logger.warning(f"Groq SDK failed, falling back to offline: {exc}")
                raise

        # Fallback for non-Groq OpenAI compatible endpoints
        payload = {
            "model": model_to_use,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024,
        }

        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()
            return self._extract_content(data)

        except requests.ConnectionError:
            msg = "⚠️ Could not reach the online API — falling back to offline."
            logger.error(msg)
            raise  # Let HybridHandler catch this and fall back

        except requests.Timeout:
            msg = "⚠️ Online API timed out — falling back to offline."
            logger.error(msg)
            raise

        except requests.HTTPError as exc:
            msg = f"⚠️ Online API error: {exc}"
            logger.error(msg)
            try:
                logger.error(f"Response body: {response.text}")
            except: pass
            raise

        except Exception as exc:  # noqa: BLE001
            msg = f"⚠️ Unexpected online error: {exc}"
            logger.exception(msg)
            raise

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_system_prompt(context: Optional[str] = None) -> str:
        """Compose the system prompt for the online model."""
        from core.prompts import build_system_prompt  # type: ignore[import-not-found]
        return build_system_prompt(mode="online", context=context)

    @staticmethod
    def _extract_content(data: dict) -> str:
        """Extract the assistant message from a chat completions response."""
        try:
            choices = data.get("choices", [])
            if choices:
                return choices[0]["message"]["content"].strip()
            return "⚠️ No response from online model."
        except (KeyError, IndexError, TypeError):
            return "⚠️ Could not parse online model response."
