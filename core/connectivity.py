"""
Phase-5 — Connectivity Checker
Fast, lightweight internet connectivity detection.
"""

from __future__ import annotations

import logging
import socket

logger = logging.getLogger(__name__)

# We try to open a TCP connection to a well-known, highly available host.
# Using Cloudflare DNS (1.1.1.1) on HTTPS port — it's fast and reliable.
_CHECK_HOST = "1.1.1.1"
_CHECK_PORT = 443
_TIMEOUT_SECONDS = 1


def check_internet() -> bool:
    """Return ``True`` if the machine can reach the internet.

    Uses a quick TCP socket connection (no HTTP overhead) so it adds
    minimal latency (~50-200 ms) before each AI request.
    """
    try:
        sock = socket.create_connection((_CHECK_HOST, _CHECK_PORT), timeout=_TIMEOUT_SECONDS)
        sock.close()
        logger.debug("Internet check: ONLINE")
        return True
    except (OSError, socket.timeout):
        logger.debug("Internet check: OFFLINE")
        return False
