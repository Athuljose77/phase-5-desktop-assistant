"""
Phase-5 — File Reader
Reads text files from disk so their contents can be sent to the AI.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# Maximum file size we're willing to read (512 KB).
MAX_FILE_SIZE = 512 * 1024


def read_file(path: str) -> str:
    """Read a text file and return its contents.

    Parameters
    ----------
    path : str
        Absolute or relative path to the file.

    Returns
    -------
    str
        File content on success, or a user-friendly error message.
    """
    path = os.path.expanduser(path)

    if not os.path.isfile(path):
        return f"⚠️ File not found: **{path}**"

    size = os.path.getsize(path)
    if size > MAX_FILE_SIZE:
        return (
            f"⚠️ File is too large ({size / 1024:.0f} KB). "
            f"Maximum supported size is {MAX_FILE_SIZE // 1024} KB."
        )

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError as exc:
        msg = f"⚠️ Could not read file: {exc}"
        logger.error(msg)
        return msg
