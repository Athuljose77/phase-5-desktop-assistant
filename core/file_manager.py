"""
Phase-5 — Natural Language File Navigator
Provides offline, deterministic file-system navigation restricted to the
user's home directory tree. No LLM involved.
"""

from __future__ import annotations

import os
import logging
from typing import TypedDict

logger = logging.getLogger(__name__)

# The root users are allowed to browse — navigation cannot escape this.
HOME_ROOT: str = os.path.expanduser("~")


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

class NavResult(TypedDict):
    """Structured result returned by list_directory / change_directory."""
    path: str            # Absolute path that is now current
    folders: list[str]  # Subdirectory names (sorted)
    files: list[str]    # File names (sorted)
    message: str         # Human-readable status / error text


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_directory(current_path: str) -> NavResult:
    """List the contents of *current_path*.

    Parameters
    ----------
    current_path : str
        The directory to list.  Must be inside HOME_ROOT.

    Returns
    -------
    NavResult
        Structured dict with ``folders``, ``files``, ``path``, and ``message``.
    """
    # Guard: stay inside home
    current_path = _safe_resolve(current_path)

    if not os.path.isdir(current_path):
        return NavResult(
            path=current_path,
            folders=[],
            files=[],
            message=f"⚠️ **{current_path}** is not a valid directory.",
        )

    try:
        entries = os.listdir(current_path)
    except PermissionError:
        return NavResult(
            path=current_path,
            folders=[],
            files=[],
            message=f"⚠️ Permission denied reading **{current_path}**.",
        )

    folders: list[str] = []
    files: list[str] = []

    for entry in entries:
        full = os.path.join(current_path, entry)
        # Skip hidden files/folders (start with .) to keep output clean
        if entry.startswith("."):
            continue
        try:
            if os.path.isdir(full):
                folders.append(entry)
            else:
                files.append(entry)
        except (PermissionError, OSError):
            pass  # Skip entries we can't stat

    folders.sort(key=str.lower)
    files.sort(key=str.lower)

    return NavResult(
        path=current_path,
        folders=folders,
        files=files,
        message="ok",
    )


def change_directory(current_path: str, folder_name: str) -> NavResult:
    """Navigate into *folder_name* relative to *current_path*, or go up.

    Supports:
    - A folder name, e.g. ``"Documents"``
    - ``".."`` or ``"back"`` / ``"up"`` to go one level up
    - An absolute path (filtered through the safety guard)

    Parameters
    ----------
    current_path : str
        The directory the user is currently in.
    folder_name : str
        The destination to navigate to.

    Returns
    -------
    NavResult
        Contains the new ``path``, listing, and a status ``message``.
    """
    folder_name = folder_name.strip()

    # Normalise "go back" aliases → ".."
    if folder_name.lower() in ("back", "up", "..", "go back", "go up", "parent"):
        folder_name = ".."

    # Build candidate target
    if folder_name == "..":
        target = os.path.dirname(current_path)
    elif os.path.isabs(folder_name):
        target = folder_name
    else:
        target = os.path.join(current_path, folder_name)

    # Normalise and apply safety guard
    target = _safe_resolve(target)

    if not os.path.isdir(target):
        # Try a case-insensitive search in the current directory
        ci_match = _case_insensitive_find(current_path, folder_name)
        if ci_match:
            target = ci_match
        else:
            return NavResult(
                path=current_path,         # stay where we are
                folders=[],
                files=[],
                message=f"⚠️ Folder **{folder_name}** not found in {current_path}.",
            )

    # List the new directory and return
    result = list_directory(target)
    result["message"] = f"📂 Entered **{os.path.basename(target) or target}**"
    return result


# ---------------------------------------------------------------------------
# Formatting helper
# ---------------------------------------------------------------------------

def format_nav_result(result: NavResult) -> str:
    """Convert a NavResult into a monospace-friendly display string."""
    if result["message"].startswith("⚠️"):
        return result["message"]

    lines: list[str] = []
    lines.append(f"📍 **Current Path:** `{result['path']}`")
    lines.append("")

    if result["folders"]:
        lines.append("📁 **Folders:**")
        for f in result["folders"]:
            lines.append(f"  📁 {f}")
    else:
        lines.append("📁 **Folders:** *(none)*")

    lines.append("")

    if result["files"]:
        lines.append("📄 **Files:**")
        for f in result["files"]:
            lines.append(f"  📄 {f}")
    else:
        lines.append("📄 **Files:** *(none)*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_resolve(path: str) -> str:
    """Return the absolute, normalised version of *path*, clamped to HOME_ROOT."""
    resolved = os.path.normpath(os.path.abspath(path))
    # Clamp: if the resolved path escapes the home tree, return home root.
    if not resolved.startswith(HOME_ROOT):
        logger.warning(
            "Navigation blocked: '%s' is outside home dir. Returning home.", resolved
        )
        return HOME_ROOT
    return resolved


def _case_insensitive_find(directory: str, name: str) -> str | None:
    """Return the first entry in *directory* whose name matches *name* (case-insensitive)."""
    try:
        for entry in os.listdir(directory):
            if entry.lower() == name.lower() and os.path.isdir(
                os.path.join(directory, entry)
            ):
                return os.path.join(directory, entry)
    except (PermissionError, OSError):
        pass
    return None
