"""
Phase-5 — Main Entry Point
Wires the GUI, AI handler, command handler, memory handler, and file
reader together.
"""

from __future__ import annotations

import logging
import re
import sys
from typing import Optional

from PyQt6.QtWidgets import QApplication  # type: ignore[import-not-found]

# ── First-run setup: show dialog if API key is missing ───────────────────────
from setup_wizard import run_setup_if_needed  # type: ignore[import-not-found]
run_setup_if_needed()

from config import (  # type: ignore[import-not-found]
    OFFLINE_MODEL,
    OLLAMA_URL,
    ONLINE_API_KEY,
    ONLINE_BASE_URL,
    ONLINE_MODEL,
)
from core.command_handler import CommandHandler  # type: ignore[import-not-found]
from core.file_reader import read_file  # type: ignore[import-not-found]
from core.file_manager import list_directory, change_directory, format_nav_result  # type: ignore[import-not-found]  # NL File Nav
from core.hybrid_handler import HybridAIHandler  # type: ignore[import-not-found]
from core.memory_handler import MemoryHandler  # type: ignore[import-not-found]
from core.system_control import SystemControl  # type: ignore[import-not-found]
from gui import MainWindow, WorkerThread  # type: ignore[import-not-found]
from PyQt6.QtCore import QThread, pyqtSignal # type: ignore[import-not-found]
import time

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-28s  %(levelname)-7s  %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Startup Diagnostics (printed to console)
# ---------------------------------------------------------------------------
print("\n" + "=" * 50)
print("  Phase-5 — Startup Diagnostics")
print("=" * 50)
print(f"  API Key Loaded : {'YES (' + ONLINE_API_KEY[:5] + '...)' if ONLINE_API_KEY and ONLINE_API_KEY != 'your-groq-api-key-here' else 'NO (key missing or placeholder)'}")  # type: ignore[index]
print(f"  Online Model   : {ONLINE_MODEL}")
print(f"  Offline Model  : {OFFLINE_MODEL}")

from core.connectivity import check_internet  # type: ignore[import-not-found]
_startup_internet = check_internet()
print(f"  Internet Check : {'CONNECTED' if _startup_internet else 'NO CONNECTION'}")

if ONLINE_API_KEY and ONLINE_API_KEY != "your-groq-api-key-here" and _startup_internet:
    print(f"  Mode           : [ONLINE] (Groq)")
elif ONLINE_API_KEY and ONLINE_API_KEY != "your-groq-api-key-here":
    print(f"  Mode           : [OFFLINE] (no internet)")
else:
    print(f"  Mode           : [OFFLINE] (no API key)")
print("=" * 50 + "\n")

# =====================================================================
# Proactive Diagnostics Thread
# =====================================================================

class DiagnosticsThread(QThread):
    """Monitors system health in the background and emits warnings."""
    warning = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent) # type: ignore[call-arg]
        self.running = True

    def run(self):
        while self.running:
            try:
                info = SystemControl.get_system_info()
                if "error" not in info:
                    ram_used = float(info.get('ram_percent_used', '0').replace('%', ''))
                    
                    # Alert if RAM is over 90%
                    if ram_used > 90.0:
                        self.warning.emit(f"⚠️ **System Alert**: High memory usage detected ({ram_used}%). Consider closing some applications.")
                        
                    # We can add battery warnings here too if psutil supports it
                    import psutil  # type: ignore[import-not-found, import]
                    battery = psutil.sensors_battery()
                    if battery and battery.percent < 20 and not battery.power_plugged:
                        self.warning.emit(f"🔋 **Battery Alert**: Battery is running low ({battery.percent}%). Please plug in your PC.")
            except Exception as e:
                logger.debug(f"Diagnostics check failed: {e}")
                
            # Check every 5 minutes
            time.sleep(300)

    def stop(self):
        self.running = False


# =====================================================================
# Application Controller
# =====================================================================

class Phase5App:
    """Orchestrates all Phase-5 subsystems.

    * Receives user input from the GUI.
    * Dispatches to the command handler or AI handler.
    * Keeps memory/context updated.
    """

    def __init__(self) -> None:
        self.ai = HybridAIHandler(
            api_key=ONLINE_API_KEY,
            online_model=ONLINE_MODEL,
            online_base_url=ONLINE_BASE_URL,
            offline_model=OFFLINE_MODEL,
            ollama_url=OLLAMA_URL,
        )
        self.memory = MemoryHandler()
        self.cmd = CommandHandler()
        self.window = MainWindow()

        # --- Natural Language File Navigator state (NL File Nav) -----------
        import os as _os
        self.current_path: str = _os.path.expanduser("~")  # start at home dir

        # Keep a reference to the active worker so it isn't GC'd
        self._worker: WorkerThread | None = None

        # Set initial mode indicator based on actual connectivity
        if self.ai._api_key_valid and _startup_internet:
            self.window.update_mode_indicator("online")
        else:
            self.window.update_mode_indicator("offline")

        # Connect the GUI's "user sent a message" signal
        self.window.user_message.connect(self._handle_input)
        
        # Start Diagnostics
        self._diagnostics = DiagnosticsThread()
        self._diagnostics.warning.connect(self.window.append_system)
        self._diagnostics.start()

    # ------------------------------------------------------------------
    # Slot: incoming user message
    # ------------------------------------------------------------------

    def _handle_input(self, text: str) -> None:
        """Route user input to the correct handler."""

        # --- 1. Check for name statements & persist -----------------------
        detected_name = self.memory.detect_name_in_message(text)
        if detected_name:
            self.memory.set_user_name(detected_name)
            logger.info("Stored user name: %s", detected_name)

        # --- 2. Parse for commands ----------------------------------------
        cmd_type, arg = self.cmd.parse(text)

        if cmd_type == "open" and arg:
            result = self.cmd.execute_open(arg)
            self.window.append_system(result)
            self.memory.add_to_history("user", text)
            self.memory.add_to_history("assistant", result)
            return

        if cmd_type == "read" and arg:
            file_content = read_file(arg)
            if file_content.startswith("⚠️"):
                self.window.append_system(file_content)
                return
            # Send file content + user instruction to AI
            prompt = (
                f"The user asked you to read a file. Here is the content of "
                f"**{arg}**:\n\n```\n{file_content}\n```\n\n"
                f"Please analyze or summarize this file."
            )
            self._send_to_ai(prompt, text)
            return
            
        if cmd_type == "learn" and arg:
            file_content = read_file(arg)
            if file_content.startswith("⚠️"):
                self.window.append_system(file_content)
                return
            self.window.append_system(f"🧠 Learning from **{arg}**...")
            import os
            basename = os.path.basename(arg)
            result = self.memory.ingest_document(file_content, basename)
            self.window.append_system(result)
            return



        # --- System Control Dispatch --------------------------------------
        
        if cmd_type == "volume":
            # arg is string "50", convert to int
            try:
                level = int(str(arg)) if arg else 50
                msg = SystemControl.set_volume(level)
            except ValueError:
                msg = "⚠️ Invalid volume level."
            self.window.append_system(msg)
            return

        if cmd_type == "mute":
            self.window.append_system(SystemControl.mute_volume())
            return
            
        if cmd_type == "unmute":
            self.window.append_system(SystemControl.unmute_volume())
            return

        if cmd_type == "brightness":
            try:
                level = int(str(arg)) if arg else 50
                msg = SystemControl.set_brightness(level)
            except ValueError:
                msg = "⚠️ Invalid brightness level."
            self.window.append_system(msg)
            return

        if cmd_type == "screenshot":
            self.window.append_system(SystemControl.take_screenshot())
            return
            
        if cmd_type == "vision":
            self.window.append_system("📸 Capturing screen for analysis...")
            image_path = SystemControl.get_screenshot_path()
            if not image_path:
                 self.window.append_system("⚠️ Failed to capture screen.")
                 return
                 
            # If there's an argument, use that as the prompt (e.g. "what is this error")
            prompt = str(arg) if arg else "Please analyze my current screen and tell me what you see."
            if "vision" in text.lower():
                 # Keep original text if they explicitly triggered it with a phrase 
                 prompt = text
                 
            self._send_to_ai(prompt, text, image_path=image_path)
            return

        if cmd_type == "lock":
            self.window.append_system(SystemControl.lock_screen())
            return

        if cmd_type == "close_app":
            if arg:
                self.window.append_system(SystemControl.close_app(arg))
            else:
                self.window.append_system("⚠️ Which app should I close?")
            return

        # --- File Operations -----------------------------------------------
        if cmd_type == "open_file":
            if arg:
                self.window.append_system(SystemControl.open_file(arg))
            else:
                self.window.append_system("⚠️ Which file should I open?")
            return

        if cmd_type == "open_with":
            if arg and "|" in arg:  # type: ignore[operator]
                filepath, app = arg.split("|", 1)  # type: ignore[union-attr]
                self.window.append_system(
                    SystemControl.open_file_with_app(filepath.strip(), app.strip())
                )
            else:
                self.window.append_system("⚠️ Please specify a file and an app.")
            return

        if cmd_type == "search_file":
            if arg:
                found = SystemControl.search_file(arg)
                if found:
                    self.window.append_system(f"🔍 Found: **{found}**")
                    # Also open it
                    self.window.append_system(SystemControl.open_file(found))
                else:
                    self.window.append_system(f"⚠️ Could not find **{arg}** in your folders.")
            return

        if cmd_type == "list_files":
            self.window.append_system(SystemControl.list_files(arg))
            return

        if cmd_type == "create_folder":
            if arg:
                self.window.append_system(SystemControl.create_folder(arg))
            else:
                self.window.append_system("⚠️ What should the folder be called?")
            return

        if cmd_type == "delete_file":
            if arg:
                self.window.append_system(SystemControl.delete_file(arg))
            else:
                self.window.append_system("⚠️ Which file should I delete?")
            return

        if cmd_type == "rename_file":
            if arg and "|" in arg:  # type: ignore[operator]
                old, new = arg.split("|", 1)  # type: ignore[union-attr]
                self.window.append_system(SystemControl.rename_file(old.strip(), new.strip()))
            else:
                self.window.append_system("⚠️ Please specify what to rename and the new name.")
            return

        if cmd_type == "copy_file":
            if arg and "|" in arg:  # type: ignore[operator]
                src, dest = arg.split("|", 1)  # type: ignore[union-attr]
                self.window.append_system(SystemControl.copy_file(src.strip(), dest.strip()))
            else:
                self.window.append_system("⚠️ Please specify the file and destination.")
            return

        if cmd_type == "move_file":
            if arg and "|" in arg:  # type: ignore[operator]
                src, dest = arg.split("|", 1)  # type: ignore[union-attr]
                self.window.append_system(SystemControl.move_file(src.strip(), dest.strip()))
            else:
                self.window.append_system("⚠️ Please specify the file and destination.")
            return

        # --- Power Management ----------------------------------------------
        if cmd_type == "shutdown":
            self.window.append_system(SystemControl.shutdown())
            return
        if cmd_type == "restart":
            self.window.append_system(SystemControl.restart())
            return
        if cmd_type == "sleep":
            self.window.append_system(SystemControl.sleep())
            return

        # --- WiFi ----------------------------------------------------------
        if cmd_type == "wifi":
            enable = (arg == "on") if arg else True
            self.window.append_system(SystemControl.toggle_wifi(enable))
            return

        # --- URL -----------------------------------------------------------
        if cmd_type == "open_url":
            if arg and "|" in arg:  # type: ignore[operator]
                url, browser = arg.split("|", 1)  # type: ignore[union-attr]
                self.window.append_system(
                    SystemControl.open_url(url.strip(), browser.strip())
                )
            elif arg:
                self.window.append_system(SystemControl.open_url(arg))
            return

        if cmd_type == "specs":
            info = SystemControl.get_system_info()
            
            # Format as plain text so the small model doesn't misread JSON
            if "error" in info:
                self.window.append_system(f"⚠️ Could not read specs: {info['error']}")
                return

            specs_text = (
                f"Operating System: {info.get('os', 'Unknown')}\n"
                f"Processor: {info.get('processor', 'Unknown')}\n"
                f"CPU Cores: {info.get('cpu_cores_physical', '?')} physical, "
                f"{info.get('cpu_cores_logical', '?')} logical\n"
                f"CPU Speed: {info.get('cpu_freq_current', 'Unknown')}\n"
                f"Total RAM: {info.get('ram_total', 'Unknown')}\n"
                f"Available RAM: {info.get('ram_available', 'Unknown')}\n"
                f"RAM Usage: {info.get('ram_percent_used', 'Unknown')}"
            )
            
            user_question = arg if arg else "What are my system specs?"
            
            prompt = (
                f"Here are the user's actual system specifications:\n\n"
                f"{specs_text}\n\n"
                f"The user asked: {user_question}\n"
                f"Present these specs clearly. Do not change the values."
            )
            
            self._send_to_ai(prompt, user_question)  # type: ignore[arg-type]
            return

        # --- Email -------------------------------------------------------
        if cmd_type == "email" and arg:
            parts = str(arg).split("|", 2)
            to      = parts[0].strip()
            subject = parts[1].strip() if len(parts) > 1 else "Message from Phase-5"
            body    = parts[2].strip() if len(parts) > 2 else ""
            self.window.append_system(f"📧 Sending email to **{to}**...")
            result = SystemControl.send_email(to, subject, body)
            self.window.append_system(result)
            self.memory.add_to_history("user", text)
            self.memory.add_to_history("assistant", result)
            return

        # --- WhatsApp --------------------------------------------------
        if cmd_type == "whatsapp" and arg:
            parts = str(arg).split("|", 1)
            contact = parts[0].strip()
            msg = parts[1].strip() if len(parts) > 1 else ""
            self.window.append_system(f"📱 Sending WhatsApp message to **{contact}**...")
            result = SystemControl.whatsapp_message(contact, msg)
            self.window.append_system(result)
            self.memory.add_to_history("user", text)
            self.memory.add_to_history("assistant", result)
            return

        # -------------------------------------------------------------------
        # Natural Language File Navigation (NL File Nav)
        # Routed here from command_handler; never sent to the LLM.
        # -------------------------------------------------------------------

        if cmd_type == "nav_list":
            import os as _os
            # Optional: arg holds an explicit folder name (e.g. "Downloads")
            if arg:
                # Resolve well-known common names to full paths first
                _COMMON = {
                    "downloads": _os.path.join(_os.path.expanduser("~"), "Downloads"),
                    "documents": _os.path.join(_os.path.expanduser("~"), "Documents"),
                    "desktop":   _os.path.join(_os.path.expanduser("~"), "Desktop"),
                    "pictures":  _os.path.join(_os.path.expanduser("~"), "Pictures"),
                    "videos":    _os.path.join(_os.path.expanduser("~"), "Videos"),
                    "music":     _os.path.join(_os.path.expanduser("~"), "Music"),
                }
                candidate = _COMMON.get(str(arg).lower())
                if candidate and _os.path.isdir(str(candidate)):
                    target_path = str(candidate)
                else:
                    target_path = _os.path.join(self.current_path, str(arg))
                result = list_directory(target_path)
            else:
                result = list_directory(self.current_path)
            self.window.append_system(format_nav_result(result))
            return

        if cmd_type == "nav_enter" and arg:
            result = change_directory(self.current_path, arg)
            # Update persistent navigation state on successful entry
            if not result["message"].startswith("⚠️"):
                self.current_path = result["path"]
            self.window.append_system(format_nav_result(result))
            return

        if cmd_type == "nav_back":
            result = change_directory(self.current_path, "..")
            self.current_path = result["path"]
            self.window.append_system(format_nav_result(result))
            return

        # --- 3. Default: regular chat ------------------------------------
        self._send_to_ai(text, text)

    # ------------------------------------------------------------------
    # AI request (runs on WorkerThread)
    # ------------------------------------------------------------------

    def _send_to_ai(self, prompt: str, original_text: str, image_path: Optional[str] = None) -> None:
        """Fire off a background worker to call the AI (online or offline)."""
        self.window.set_loading(True)

        context = self.memory.get_context_string(rag_query=original_text)

        self._worker = WorkerThread(self.ai, prompt, context, image_path=image_path)
        self._worker.mode_changed.connect(self.window.update_mode_indicator)
        self._worker.result_ready.connect(
            lambda resp: self._on_ai_response(resp, original_text)
        )
        self._worker.start()

    def _on_ai_response(self, response: str, original_text: str) -> None:
        """Handle the completed AI response back on the main thread.

        If the AI embedded a |||CMD:type:arg||| tag, extract it, execute
        the system command, and display the cleaned response.
        """
        self.window.set_loading(False)

        # --- Parse for AI-detected command tags ---
        clean_response, cmd_result = self._parse_and_execute_cmd(response)

        self.window.append_assistant(clean_response)
        if cmd_result:
            self.window.append_system(cmd_result)

        # Persist conversation
        self.memory.add_to_history("user", original_text)
        self.memory.add_to_history("assistant", clean_response)

        # --- Speak the response (TTS) ---
        try:
            from core.voice_handler import speak  # type: ignore[import-not-found]
            # Strip markdown/formatting for cleaner speech
            import re as _re
            speech_text = _re.sub(r"\*\*(.+?)\*\*", r"\1", clean_response)
            speech_text = _re.sub(r"`[^`]+`", "", speech_text)
            speech_text = _re.sub(r"<!--.*?-->", "", speech_text)
            speech_text = speech_text.strip()
            if speech_text and len(speech_text) < 500:  # Don't speak very long responses
                if self.window.is_tts_enabled():
                    speak(speech_text)
        except ImportError:
            pass  # TTS not installed — silent mode

    # ------------------------------------------------------------------
    # AI command-tag parser
    # ------------------------------------------------------------------

    # Known CMD types for fuzzy correction of model output
    _KNOWN_CMD_TYPES = [
        "open", "open_url", "open_file", "open_with",
        "volume", "mute", "unmute",
        "brightness", "screenshot", "vision",
        "shutdown", "restart", "sleep", "lock",
        "close_app", "list_files", "create_folder",
        "delete_file", "rename_file", "copy_file", "move_file",
        "file_info", "wifi", "specs",
    ]
    # Match |||CMD:type:arg||| — also accept || or | variants from small models
    _CMD_PATTERN = re.compile(r"\|{1,3}CMD:([\w_]+):(.*?)\|{1,3}", re.IGNORECASE)

    def _parse_and_execute_cmd(self, response: str) -> tuple[str, str | None]:
        """Extract and execute a |||CMD:type:arg||| tag from *response*.

        Applies fuzzy correction on the cmd_type so minor model output
        typos (e.g. 'brithness') are mapped to the correct command.
        Returns (cleaned_response, command_result_message_or_None).
        """
        import difflib
        match = self._CMD_PATTERN.search(response)
        if not match:
            return response, None

        raw_type = match.group(1).lower().strip()
        cmd_arg  = match.group(2).strip() or None

        # Fuzzy-correct the cmd type in case the model mangles it slightly
        corrections = difflib.get_close_matches(raw_type, self._KNOWN_CMD_TYPES, n=1, cutoff=0.72)
        cmd_type = corrections[0] if corrections else raw_type

        # Strip the tag from the displayed response
        clean = self._CMD_PATTERN.sub("", response).rstrip()

        # Dispatch the command
        result = self._execute_ai_command(cmd_type, cmd_arg)
        return clean, result

    def _execute_ai_command(self, cmd_type: str, arg: str | None) -> str:
        """Execute a system command identified by the AI."""
        try:
            if cmd_type == "brightness":
                level = int(arg) if arg else 50
                return SystemControl.set_brightness(level)

            if cmd_type == "volume":
                level = int(arg) if arg else 50
                return SystemControl.set_volume(level)

            if cmd_type == "mute":
                return SystemControl.mute_volume()

            if cmd_type == "unmute":
                return SystemControl.unmute_volume()

            if cmd_type == "screenshot":
                return SystemControl.take_screenshot()

            if cmd_type == "lock":
                return SystemControl.lock_screen()

            if cmd_type == "shutdown":
                return SystemControl.shutdown()

            if cmd_type == "restart":
                return SystemControl.restart()

            if cmd_type == "sleep":
                return SystemControl.sleep()

            if cmd_type == "wifi_on":
                return SystemControl.toggle_wifi("on")

            if cmd_type == "wifi_off":
                return SystemControl.toggle_wifi("off")

            if cmd_type == "open" and arg:
                result = self.cmd.execute_open(arg)
                return result

            if cmd_type == "open_url" and arg:
                return SystemControl.open_url(arg)

            if cmd_type == "close_app" and arg:
                return SystemControl.close_app(arg)

            # File management commands
            if cmd_type == "list_files":
                return SystemControl.list_files(arg)

            if cmd_type == "create_folder" and arg:
                return SystemControl.create_folder(arg)

            if cmd_type == "delete_file" and arg:
                return SystemControl.delete_file(arg)

            if cmd_type == "rename_file" and arg and "|" in arg:
                old, new = arg.split("|", 1)
                return SystemControl.rename_file(old.strip(), new.strip())

            if cmd_type == "copy_file" and arg and "|" in arg:
                src, dest = arg.split("|", 1)
                return SystemControl.copy_file(src.strip(), dest.strip())

            if cmd_type == "move_file" and arg and "|" in arg:
                src, dest = arg.split("|", 1)
                return SystemControl.move_file(src.strip(), dest.strip())

            if cmd_type == "file_info" and arg:
                return SystemControl.file_info(arg)

            # --- New automation commands ---

            if cmd_type == "web_search" and arg:
                return SystemControl.web_search(arg)

            if cmd_type == "type_text" and arg:
                return SystemControl.type_text(arg)

            if cmd_type == "clipboard_copy" and arg:
                return SystemControl.clipboard_copy(arg)

            if cmd_type == "media_control" and arg:
                return SystemControl.media_control(arg)

            if cmd_type == "set_timer" and arg:
                try:
                    secs = int(arg)
                    return SystemControl.set_timer(secs)
                except ValueError:
                    return "⚠️ Invalid timer duration."

            if cmd_type in ("whatsapp", "whatsapp_message") and arg:
                parts = arg.split("|", 1)
                contact = parts[0].strip()
                msg = parts[1].strip() if len(parts) > 1 else ""
                return SystemControl.whatsapp_message(contact, msg)

            return f"⚠️ Unknown AI command: {cmd_type}"

        except Exception as exc:  # noqa: BLE001
            return f"⚠️ Command failed: {exc}"

    # ------------------------------------------------------------------
    # Show window
    # ------------------------------------------------------------------

    def show(self) -> None:
        self.window.show()


# =====================================================================
# Entry point
# =====================================================================

def main() -> None:
    app = QApplication(sys.argv)
    phase5 = Phase5App()
    
    # ------------------------------------------------------------------
    # Global Hotkey Setup (Alt + Space)
    # ------------------------------------------------------------------
    try:
        import keyboard  # type: ignore[import-not-found, import]
        
        def bring_to_front():
            # If minimized, restore it
            if phase5.window.isMinimized():
                phase5.window.showNormal()
            
            # Show and bring to front
            phase5.window.show()
            phase5.window.raise_()
            phase5.window.activateWindow()
            
            # Focus the input field
            phase5.window.input_field.setFocus()

        # Register the hotkey
        keyboard.add_hotkey('alt+space', bring_to_front, suppress=True) # suppress=True tries to prevent other apps from seeing it
        logger.info("Registered global hotkey: Alt + Space")
    except ImportError:
        logger.warning("keyboard library not found. Global hotkey will not work.")
    except Exception as e:
        logger.error(f"Failed to register global hotkey: {e}. (May require administrator privileges)")

    phase5.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
