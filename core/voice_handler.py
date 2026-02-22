"""
Phase-5 — Voice I/O Handler
Speech-to-text input and text-to-speech output for hands-free interaction.

STT: Runs faster-whisper in a SUBPROCESS so its native C++ libs (CTranslate2/OpenMP)
     cannot hard-abort the parent PyQt process.
TTS: pyttsx3 — fully local.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Prevent OpenMP crashes on Windows if any C++ libs are loaded in this process
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# ---------------------------------------------------------------------------
# Text-to-Speech (always offline with pyttsx3)
# ---------------------------------------------------------------------------

_tts_lock = threading.Lock()


def speak(text: str) -> None:
    """Speak *text* using the local TTS engine (non-blocking).

    Runs in a background thread so it doesn't freeze the GUI.
    """
    def _run() -> None:
        try:
            import pyttsx3  # type: ignore[import-not-found]
            with _tts_lock:
                engine = pyttsx3.init()
                engine.setProperty("rate", 175)
                engine.setProperty("volume", 0.9)

                voices = engine.getProperty("voices")
                if voices and len(voices) > 1:
                    engine.setProperty("voice", voices[1].id)

                engine.say(text)
                engine.runAndWait()
                engine.stop()
        except ImportError:
            logger.warning("pyttsx3 not installed — TTS unavailable.")
        except Exception as exc:  # noqa: BLE001
            logger.error("TTS failed: %s", exc)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


# ---------------------------------------------------------------------------
# Speech-to-Text — subprocess isolation
# ---------------------------------------------------------------------------

def listen(timeout: int = 8, phrase_limit: int = 15) -> Optional[str]:
    """Listen for speech and return transcribed text.

    Spawns ``transcribe_worker.py`` in a separate process so that
    faster-whisper's native C++ runtime cannot crash the PyQt GUI.

    Protocol (via stdout):
      READY   — microphone is open, user should speak
      OK:<text>  — success
      ERR:<msg>  — failure

    Raises
    ------
    RuntimeError
        With a human-readable error message.
    """
    worker_script = Path(__file__).parent / "transcribe_worker.py"
    if not worker_script.exists():
        raise RuntimeError(
            "transcribe_worker.py not found. "
            "Please re-clone / re-install Phase-5."
        )

    try:
        proc = subprocess.Popen(
            [sys.executable, str(worker_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        output_lines: list[str] = []

        if proc.stdout:
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                if line == "READY":
                    logger.info("Microphone open — listening for speech...")
                else:
                    output_lines.append(line)

        proc.wait(timeout=timeout + phrase_limit + 15)

        stderr_text = proc.stderr.read() if proc.stderr else ""
        if stderr_text:
            logger.debug("Worker stderr: %s", stderr_text[:400])

        if not output_lines:
            raise RuntimeError("Voice worker produced no output. Check microphone settings.")

        last = output_lines[-1]
        if last.startswith("OK:"):
            return last[3:].strip()
        if last.startswith("ERR:"):
            raise RuntimeError(last[4:].strip())

        raise RuntimeError(f"Unexpected worker output: {last}")

    except subprocess.TimeoutExpired:
        proc.kill()
        raise RuntimeError("Voice input timed out — try speaking sooner.")
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Voice input error: {exc}")


def is_voice_available() -> bool:
    """Return True if STT or TTS dependencies are installed."""
    available = {"stt": False, "tts": False}
    try:
        import faster_whisper  # type: ignore[import-not-found, import]  # noqa: F401
        import speech_recognition  # type: ignore[import-not-found, import]  # noqa: F401
        available["stt"] = True
    except ImportError:
        pass
    try:
        import pyttsx3  # type: ignore[import-not-found]  # noqa: F401
        available["tts"] = True
    except ImportError:
        pass
    return available["stt"] or available["tts"]
