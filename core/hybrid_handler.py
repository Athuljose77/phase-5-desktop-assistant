"""
Phase-5 — Hybrid AI Handler
Automatically switches between online (Groq) and offline (Ollama) models
based on internet connectivity and configuration.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class HybridAIHandler:
    """Orchestrator that routes AI requests to the best available backend.

    Behavior
    --------
    1. If internet is available **and** an API key is configured → Online (Groq)
    2. Otherwise → Offline (Ollama / Qwen)
    3. If an online request fails mid-flight → automatic fallback to offline

    The ``current_mode`` property reports which backend was last used so the
    GUI can display a status indicator.
    """

    def __init__(
        self,
        api_key: str = "",
        online_model: str = "llama-3.3-70b-versatile",
        online_base_url: str = "https://api.groq.com/openai/v1/chat/completions",
        offline_model: str = "qwen2.5:1.5b",
        ollama_url: str = "http://localhost:11434/api/generate",
    ) -> None:
        from core.online_handler import OnlineHandler  # type: ignore[import-not-found]
        from core.offline_handler import OfflineHandler  # type: ignore[import-not-found]

        # Online backend
        self._online: OnlineHandler | None = None
        self._api_key_valid = bool(api_key) and api_key != "your-groq-api-key-here"
        if self._api_key_valid:
            self._online = OnlineHandler(
                api_key=api_key,
                model=online_model,
                base_url=online_base_url,
            )

        # Offline backend (always available)
        self._offline = OfflineHandler(
            model=offline_model,
            base_url=ollama_url,
        )

        # Track which mode was last used
        self._current_mode: str = "offline"

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def current_mode(self) -> str:
        """Return ``"online"`` or ``"offline"`` based on the last request."""
        return self._current_mode

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_response(
        self,
        prompt: str,
        context: Optional[str] = None,
        on_mode_decided: Optional[callable] = None,  # type: ignore[type-arg]
        image_path: Optional[str] = None,
    ) -> str:
        """Generate a response using the best available backend.

        Parameters
        ----------
        prompt : str
            The user's message or enriched prompt.
        context : str | None
            Memory / conversation context for the system prompt.
        on_mode_decided : callable | None
            Optional callback fired immediately when the mode is chosen,
            before the AI request starts. Receives ``"online"`` or ``"offline"``.
        image_path : str | None
            Optional path to an image to analyze.

        Returns
        -------
        str
            The AI-generated response text.
        """
        from core.connectivity import check_internet  # type: ignore[import-not-found]

        # Try online first if configured
        if self._online and self._api_key_valid:
            logger.info("Checking internet...")
            t0 = time.time()
            is_connected = check_internet()
            logger.info(f"Internet check took {time.time()-t0:.2f}s: {is_connected}")
            if is_connected:
                try:
                    logger.info("Using ONLINE model (Groq: %s)", self._online.model)
                    self._current_mode = "online"
                    if on_mode_decided:
                        on_mode_decided("online")
                    logger.info("Calling online_handler.generate_response...")
                    t1 = time.time()
                    res = self._online.generate_response(prompt, context, image_path=image_path)
                    logger.info(f"online_handler.generate_response took {time.time()-t1:.2f}s")
                    return res
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Online request failed (%s), falling back to offline.",
                        exc,
                    )
                    # Fall through to offline
            else:
                logger.info("No internet detected — using offline model.")

        if image_path:
             logger.warning("Vision is only supported in online mode right now. Processing text only.")

        # Offline fallback
        logger.info("Using OFFLINE model (Ollama: %s)", self._offline.model)
        self._current_mode = "offline"
        if on_mode_decided:
            on_mode_decided("offline")

        # ── Inject live web search for current events queries ──────────────────
        # This gives the offline model real-time context even without internet access
        # to the AI API, by doing a quick DuckDuckGo lookup and prepending results.
        try:
            from core.web_search import is_current_events_query, search_web  # type: ignore[import-not-found]
            if is_current_events_query(prompt):
                logger.info("Current events query detected — fetching web results...")
                web_results = search_web(prompt, max_results=3)
                if web_results:
                    search_context = (
                        f"[LIVE WEB SEARCH RESULTS for: '{prompt}']\n"
                        f"{web_results}\n"
                        f"[Use the above real-time data to supplement your answer. "
                        f"Cite it rather than guessing.]\n"
                    )
                    context = (context or "") + "\n\n" + search_context
                    logger.info("Injected %d chars of web context.", len(search_context))
        except Exception as exc:
            logger.debug("Web search injection skipped: %s", exc)

        return self._offline.generate_response(prompt, context)

