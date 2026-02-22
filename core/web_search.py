"""
Phase-5 — Web Search Module
Fetches real-time search results using DuckDuckGo Instant Answer API.
No API key required. Used to inject current event context into AI prompts.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Keywords that signal user is asking about current events
_CURRENT_EVENTS_KEYWORDS = [
    "current", "latest", "today", "this week", "this month", "this year",
    "recent", "news", "now", "right now", "currently", "2024", "2025", "2026",
    "who is", "who won", "who is the president", "who is the pm", "prime minister",
    "what happened", "what is happening", "breaking", "update", "score",
    "match", "election", "winner", "champion",
]


def is_current_events_query(query: str) -> bool:
    """Return True if the query looks like a current events / news question."""
    q_lower = query.lower()
    return any(kw in q_lower for kw in _CURRENT_EVENTS_KEYWORDS)


def search_web(query: str, max_results: int = 3) -> Optional[str]:
    """Search DuckDuckGo and return a short summary of top results.

    Uses the `duckduckgo_search` library (pip install duckduckgo_search).
    Falls back to the Instant Answer API on failure.

    Returns
    -------
    str | None
        A formatted string of search results, or None on failure.
    """
    # ── Primary: duckduckgo_search library ─────────────────────────────────────
    try:
        from ddgs import DDGS  # type: ignore[import-not-found, import]
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if results:
            lines = []
            for r in results:
                title = r.get("title", "")
                body = r.get("body", "")[:250]
                if body:
                    lines.append(f"• **{title}**: {body}")
            if lines:
                return "\n".join(lines)
    except Exception as e:
        logger.warning("duckduckgo_search library failed: %s", e)

    # ── Fallback: DuckDuckGo Instant Answer API ────────────────────────────────
    try:
        import requests  # type: ignore[import-not-found]
        response = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_redirect": "1", "no_html": "1"},
            timeout=5,
        )
        data = response.json()
        abstract = data.get("AbstractText", "").strip()
        if abstract:
            return f"• {abstract}"
    except Exception as e:
        logger.warning("DuckDuckGo Instant API failed: %s", e)

    return None
