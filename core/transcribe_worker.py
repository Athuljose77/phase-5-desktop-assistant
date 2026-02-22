"""
Phase-5 — Isolated Transcription Worker
Runs as a SUBPROCESS to isolate native C++ libs from PyQt.

Priority order for transcription:
  1. Groq Whisper API  — whisper-large-v3 quality at lightning speed (online)
  2. Local Faster-Whisper — base.en, fully offline fallback

Protocol (stdout):
  READY      — microphone is open, start speaking
  OK:<text>  — success
  ERR:<msg>  — failure
"""
import os
import sys
import io
import wave
import tempfile

# Must be set BEFORE importing CTranslate2 / faster_whisper
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# ── Load API key from .env ────────────────────────────────────────────────────
def _load_api_key() -> str:
    from pathlib import Path
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("ONLINE_API_KEY="):
            return line.split("=", 1)[1].strip()
    return ""

# ── Microphone capture ────────────────────────────────────────────────────────
try:
    import speech_recognition as sr  # type: ignore[import-not-found]
    import numpy as np               # type: ignore[import-not-found]
except ImportError as e:
    print(f"ERR:Missing dependency: {e}. Run: pip install SpeechRecognition PyAudio numpy")
    sys.exit(1)

recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = True
recognizer.energy_threshold = 400       # good starting point — adapts dynamically
recognizer.pause_threshold = 1.2        # wait 1.2s silence before stopping
recognizer.non_speaking_duration = 0.5
recognizer.dynamic_energy_adjustment_damping = 0.15
recognizer.dynamic_energy_ratio = 1.5

try:
    with sr.Microphone() as source:
        # Very short calibration (0.3s) so first words aren't cut off
        # dynamic_energy_threshold handles the rest in real-time
        recognizer.adjust_for_ambient_noise(source, duration=0.3)
        print("READY", flush=True)
        try:
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=45)
        except sr.WaitTimeoutError:
            print("ERR:No speech detected. Please speak after pressing the mic button.")
            sys.exit(1)
except Exception as exc:
    print(f"ERR:Microphone error: {exc}")
    sys.exit(1)

# ── Save audio as a WAV file in memory (for Groq API) ─────────────────────────
wav_bytes = io.BytesIO()
with wave.open(wav_bytes, "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)  # 16-bit
    wf.setframerate(16000)
    wf.writeframes(audio.get_raw_data(convert_rate=16000, convert_width=2))
wav_bytes.seek(0)

# ── Strategy 1: Groq Whisper API (fast, accurate, handles accents well) ────────
# Short example-based prompt — does NOT start with 'Transcribing' to avoid
# Whisper hallucinating continuation text when audio is unclear.
_CONTEXT_PROMPT = (
    "AI assistant voice commands. Indian English speaker. "
    "Examples: open notepad, open chrome, open excel, set volume fifty, "
    "set brightness seventy, take screenshot, what is the weather, "
    "generate python code, how to, give me a code, close chrome, "
    "shut down, restart, search for, what are my specs."
)

api_key = _load_api_key()
if api_key and api_key != "your-groq-api-key-here":
    try:
        from groq import Groq  # type: ignore[import-not-found, import]
        client = Groq(api_key=api_key)

        # Write to a temp file since Groq SDK expects a file-like with a name
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(wav_bytes.read())
            tmp_path = tmp.name

        with open(tmp_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=("audio.wav", audio_file),
                model="whisper-large-v3",      # most accurate Groq Whisper model
                response_format="text",
                language="en",
                temperature=0.0,
                prompt=_CONTEXT_PROMPT,        # KEY: biases model for accent + vocabulary
            )

        os.unlink(tmp_path)
        text = (transcription if isinstance(transcription, str) else str(transcription)).strip()

        if text:
            print(f"OK:{text}")
            sys.exit(0)
    except Exception as exc:
        # Groq failed — fall through to local transcription
        wav_bytes.seek(0)

# ── Strategy 2: Local Faster-Whisper fallback (base.en, offline) ──────────────
try:
    from faster_whisper import WhisperModel  # type: ignore[import-not-found]
except ImportError as e:
    print(f"ERR:faster_whisper not installed: {e}")
    sys.exit(1)

try:
    audio_np = np.frombuffer(
        audio.get_raw_data(convert_rate=16000, convert_width=2),
        dtype=np.int16
    ).astype(np.float32) / 32768.0

    model = WhisperModel("base.en", device="cpu", compute_type="int8")
    segments, info = model.transcribe(
        audio_np,
        beam_size=5,
        language="en",
        task="transcribe",
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=400),
        initial_prompt=_CONTEXT_PROMPT,
        condition_on_previous_text=False,  # prevents hallucination chaining
        log_prob_threshold=-0.8,           # reject low-confidence segments
        no_speech_threshold=0.7,           # skip if likely silence/noise
    )
    text = "".join(seg.text for seg in segments).strip()
except Exception as exc:
    print(f"ERR:Transcription failed: {exc}")
    sys.exit(1)

if not text:
    print("ERR:Could not understand the audio. Please speak clearly and try again.")
    sys.exit(1)

print(f"OK:{text}")
sys.exit(0)
