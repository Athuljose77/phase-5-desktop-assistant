"""
Phase-5 — Command Handler
Detects and executes system commands from user input.
"""

from __future__ import annotations

import difflib
import logging
import os
import re
import shutil
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Directories to scan for shortcuts
# ---------------------------------------------------------------------------
START_MENU_PATHS = [
    os.path.join(os.environ["ProgramData"], r"Microsoft\Windows\Start Menu\Programs"),
    os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs"),
]

# ---------------------------------------------------------------------------
# App alias map (common names → executable / launch command)
# ---------------------------------------------------------------------------
APP_ALIASES: dict[str, str] = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "paint": "mspaint.exe",
    "explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "terminal": "wt.exe",
    "chrome": "chrome",
    "firefox": "firefox",
    "vscode": "code",
    "code": "code",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
}


# ---------------------------------------------------------------------------
# Fuzzy typo correction for command trigger words
# ---------------------------------------------------------------------------
_COMMAND_TRIGGERS = [
    "open", "start", "launch", "run", "play", "watch",
    "close", "quit", "exit", "terminate", "kill",
    "search", "find", "locate", "google",
    "volume", "louder", "quieter", "softer", "mute", "unmute",
    "brightness", "bright", "dim", "dimmer", "brighter",
    "screenshot", "shutdown", "restart", "reboot", "sleep", "hibernate",
    "lock", "wifi", "read", "learn", "specs",
    "type", "write", "input",
    "email", "send", "mail",
    "copy", "clipboard",
    "timer", "remind", "alarm",
    "whatsapp", "message", "chat",
    "pause", "next", "previous", "skip", "stop", "resume",
]


def _fuzzy_correct(text: str) -> str:
    """Correct misspelled command trigger words in *text* using fuzzy matching.

    Only corrects the first 3 words (verb position) to avoid corrupting
    the argument (app name, filename, etc.).
    Requires ≥ 0.80 similarity to substitute.
    """
    words = text.split()
    corrected: list[str] = []
    for i, word in enumerate(words):
        if i <= 2:
            w_lower = word.lower()
            matches = difflib.get_close_matches(
                w_lower, _COMMAND_TRIGGERS, n=1, cutoff=0.72
            )
            if matches and matches[0] != w_lower:
                logger.debug("Fuzzy corrected '%s' -> '%s'", word, matches[0])
                corrected.append(matches[0])
                continue
        corrected.append(word)
    return " ".join(corrected)


class CommandHandler:
    """Parse user input for actionable commands (``open``, ``read``, etc.)
    and execute them.
    """

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    @staticmethod
    def parse(user_input: str) -> tuple[str, Optional[str]]:
        """Detect whether *user_input* starts with a known command keyword.

        Returns
        -------
        tuple[str, str | None]
            ``(command_type, argument)`` where *command_type* is one of
            the recognized commands, or ``"chat"`` (default).
        """
        text = user_input.strip()
        # Apply fuzzy correction so 'oepn notepad', 'shutdwon' etc. still work
        text = _fuzzy_correct(text)
        lower = text.lower()

        import re

        # --- "open X in Y" : open a file/URL with a specific app ----------
        open_in_match = re.search(
            r"(?:open|play|launch)\s+(.+?)\s+(?:in|with|using)\s+(.+?)(?:[!?.]|$)",
            lower,
            re.IGNORECASE,
        )
        if open_in_match:
            target = open_in_match.group(1).strip()
            app = open_in_match.group(2).strip()
            # Check if target looks like a URL
            if any(d in target for d in [".com", ".org", ".net", "www.", "http"]):
                return ("open_url", f"{target}|{app}")
            return ("open_with", f"{target}|{app}")

        # --- "open <URL>" : open a website --------------------------------
        url_match = re.search(
            r"(?:open|go to|visit|browse)\s+((?:https?://|www\.)\S+|[\w.-]+\.(?:com|org|net|io|dev|in|co)\S*)",
            lower,
            re.IGNORECASE,
        )
        if url_match:
            return ("open_url", url_match.group(1).strip())

        # --- "open <app>" or "start <app>" --------------------------------
        # NOTE: terminator is [!?] (no dot) so filenames like 'exp 5.pdf'
        # are captured whole rather than being cut at the period.
        open_match = re.search(
            r"^(?:(?:please|can you|could you|would you|just)\s+)?(?:open|start|launch|run)\s+(.+?)(?:\s*[!?]|$)",
            lower,
            re.IGNORECASE,
        )
        if open_match:
            arg = open_match.group(1).strip()
            # Check if it looks like a file path or has an extension
            if os.path.sep in arg or "." in arg.split()[-1]:
                return ("open_file", arg)
            return ("open", arg)

        # --- "play <file>" : open media file with default player ----------
        play_match = re.search(
            r"(?:play|watch)\s+(.+?)(?:[!?.]|$)",
            lower,
            re.IGNORECASE,
        )
        if play_match:
            return ("open_file", play_match.group(1).strip())

        # --- "search for <file>" : find a FILE (not a programming 'find') ------
        # Only trigger if the query looks like a genuine file search:
        #   - Explicitly mentions "file", "document", "folder", etc., OR
        #   - Uses phrasing like "find my X" / "search for my X"
        # Block common coding/question prefixes to avoid false positives.
        _CODING_PREFIXES = (
            "python", "code", "program", "script", "how to", "how do",
            "write a", "give me", "generate", "create a", "make a",
            "explain", "what is", "what are", "can you tell",
            "largest", "smallest", "algorithm", "function", "method",
        )
        _FILE_HINTS = (
            "file", "document", "doc", "folder", "directory", "pdf",
            ".txt", ".py", ".jpg", ".png", ".mp4", ".docx", ".xlsx",
            "my ", "the file", "the doc",
        )
        search_match = re.search(
            r"(?:search|find|locate)\s+(?:for\s+)?(?:a\s+)?(?:file\s+|document\s+|doc\s+|folder\s+)?(?:called\s+|named\s+)?(.+?)(?:[!?.]|$)",
            lower,
            re.IGNORECASE,
        )
        if search_match:
            candidate = search_match.group(1).strip()
            is_coding = any(lower.startswith(p) or f" {p} " in lower for p in _CODING_PREFIXES)
            has_file_hint = any(h in lower for h in _FILE_HINTS)
            # Only treat as file search if no coding context AND has file hint OR very short candidate
            if not is_coding and (has_file_hint or (len(candidate.split()) <= 3 and "." in candidate)):
                return ("search_file", candidate)

        # -------------------------------------------------------------------
        # Natural Language File Navigation (offline, deterministic)
        # Intents: nav_list (show contents), nav_enter (cd into folder),
        #          nav_back (go to parent directory)
        # These are checked BEFORE the generic read/learn rules so phrases
        # like "show files in Downloads" don't accidentally fall through.
        # -------------------------------------------------------------------

        # --- nav_back: "go back", "go up", "parent folder", etc. ----------
        if re.search(
            r"\b(go\s+back|go\s+up|parent\s+folder|back|up\s+one\s+level|previous\s+folder)\b",
            lower,
        ):
            return ("nav_back", None)

        # --- nav_list: "list files", "show folders", "what's here", etc. --
        nav_list_match = re.search(
            r"(?:list|show|display|what(?:'s|\s+is)\s+(?:in|here))\s+"
            r"(?:(?:all\s+)?(?:files?|folders?|contents?|directory|dir)\s+)?"
            r"(?:in\s+)?(?:(?:my|the|current|this)\s+)?"
            r"(?:directory|folder|path|location)?",
            lower,
        )
        # Also catch bare "list folders", "show files", "what's in my system", etc.
        _NAV_LIST_TRIGGERS = (
            "list files", "list folders", "show files", "show folders",
            "show contents", "list contents", "display files", "display folders",
            "what's here", "what is here", "what's in this folder",
            "show directory", "list directory", "list dir",
            "show current directory", "show current folder",
            "list my folders", "list my files",
            "show me files", "show me folders",
            "files in", "folders in", "list folders in", "list files in",
            "show files in", "show folders in",
            "what files", "what folders",
        )
        if nav_list_match or any(t in lower for t in _NAV_LIST_TRIGGERS):
            # Extract an optional explicit folder name ("list files in Downloads")
            folder_arg_match = re.search(
                r"(?:in|inside|of)\s+(?:my\s+)?([A-Za-z0-9_ .-]+?)(?:\s+folder)?(?:[!?.]|$)",
                lower,
            )
            folder_arg = folder_arg_match.group(1).strip() if folder_arg_match else None
            # Ignore common filler words that aren't real folder names
            if folder_arg in (
                "current", "this", "the", "my", "a", "system",
                "directory", "folder", "path", "location", "here",
            ):
                folder_arg = None
            return ("nav_list", folder_arg)

        # --- nav_enter: "enter", "go to", "navigate to" + folder ----------
        # IMPORTANT: 'open' is deliberately excluded here — "open X.pdf"
        # must fall through to open_file, not be treated as folder nav.
        # File-extension guard: if the target looks like a file (has a dot
        # followed by 1-5 chars), skip nav_enter entirely.
        nav_enter_match = re.search(
            r"(?:enter|go\s+(?:to|into)|navigate\s+(?:to|into)|cd|change\s+(?:to|into))\s+"
            r"(?:the\s+)?(?:(?:my\s+)?(?:downloads?|documents?|desktop|pictures?|videos?|music"
            r"|[A-Za-z0-9_ -]+?))\s*(?:folder|directory|dir)?(?:\s*[!?]|$)",
            lower,
        )
        if nav_enter_match:
            # Grab the folder name portion from group
            raw = nav_enter_match.group(0)
            # Strip leading verb phrase and trailing noise (no dot terminator)
            folder_name_match = re.search(
                r"(?:enter|go\s+(?:to|into)|navigate\s+(?:to|into)|cd|change\s+(?:to|into))\s+"
                r"(?:the\s+)?([A-Za-z0-9_ /-]+?)(?:\s+(?:folder|directory|dir))?(?:\s*[!?])?$",
                raw.strip(),
                re.IGNORECASE,
            )
            if folder_name_match:
                folder_name = folder_name_match.group(1).strip()
                # Guard: if it looks like a filename (has extension), skip nav_enter
                if re.search(r'\.[a-zA-Z0-9]{1,5}$', folder_name):
                    pass  # fall through to open_file / open handlers
                elif folder_name not in ("the", "a", "my", ""):
                    return ("nav_enter", folder_name)

        # --- Read / Learn File --------------------------------------------
        # "read file.txt" or "learn file.txt"
        match = re.search(r"\b(?:read|learn)\b\s+(.+)", lower)
        if match:
            # Check if this is a "read" vs "learn" intent based on the keyword used
            keyword_end_idx = match.start() + 5
            intent = "learn" if "learn" in lower[:keyword_end_idx] else "read"  # type: ignore[index]
            return (intent, match.group(1).strip())

        # --- Volume -------------------------------------------------------
        if "volume" in lower or re.search(r"\b(louder|quieter|softer)\b", lower):
            vol_match = re.search(r"(\d+)\s*%?", lower)
            if vol_match:
                return ("volume", vol_match.group(1))
            # No number given — still return volume with a default
            return ("volume", None)
        
        if "unmute" in lower:
            return ("unmute", None)
        if "mute" in lower:
            return ("mute", None)

        # --- Brightness ---------------------------------------------------
        if "brightness" in lower or re.search(r"\b(bright|dim|dimmer|brighter)\b", lower):
            bri_match = re.search(r"(\d+)\s*%?", lower)
            if bri_match:
                return ("brightness", bri_match.group(1))
            # No number given — still return brightness with a default
            return ("brightness", None)

        # --- Screenshot & Vision ------------------------------------------
        if "screenshot" in lower or "screen shot" in lower:
            # Check if they want to ask a question ABOUT the screen
            if any(word in lower for word in ["see", "look", "what", "analyze", "read", "explain"]):
                 return ("vision", text)
            return ("screenshot", None)
            
        if any(phrase in lower for phrase in ["what is on my screen", "what's on my screen", "look at my screen", "can you see"]):
             return ("vision", text)

        # --- Lock Screen --------------------------------------------------
        if "lock screen" in lower or "lock workstation" in lower or lower.strip() == "lock":
            return ("lock", None)

        # --- Power Management ---------------------------------------------
        if re.search(r"\b(shut\s*down|power\s*off|turn\s*off\s*(the\s+)?(computer|pc|system))\b", lower):
            return ("shutdown", None)
        if re.search(r"\b(restart|reboot)\b", lower):
            return ("restart", None)
        if re.search(r"\b(sleep|hibernate)\b", lower):
            return ("sleep", None)

        # --- WiFi ---------------------------------------------------------
        if "wifi" in lower or "wi-fi" in lower:
            if "off" in lower or "disable" in lower or "disconnect" in lower:
                return ("wifi", "off")
            if "on" in lower or "enable" in lower or "connect" in lower:
                return ("wifi", "on")

        # --- System Specs -------------------------------------------------
        specs_keywords = ["specs", "specification", "system info", "hardware info"]
        if any(k in lower for k in specs_keywords):
            return ("specs", text)

        # --- Close App ----------------------------------------------------
        close_match = re.search(
            r"^(?:(?:please|can you|just)\s+)?(?:close|quit|exit|terminate|kill)\s+(.+?)(?:[!?.]|$)",
            lower,
            re.IGNORECASE,
        )
        if close_match:
            return ("close_app", close_match.group(1).strip())

        # --- Legacy checks ------------------------------------------------
        if lower.startswith("open "):
            arg = text[5:].strip()  # type: ignore[index]
            return ("open", arg)

        if lower.startswith("read "):
            arg = text[5:].strip()  # type: ignore[index]
            return ("read", arg) if arg else ("chat", None)

        # --- File Management ----------------------------------------------

        # List files
        list_match = re.search(
            r"(?:list|show|display|what'?s?\s+in)\s+(?:me\s+)?(?:my\s+)?(?:the\s+)?(?:files?\s+)?(?:in\s+)?(?:the\s+)?(.+?)(?:[!?.]|$)",
            lower,
            re.IGNORECASE,
        )
        if list_match and any(
            kw in lower for kw in ["list", "show me", "show my", "what's in", "whats in", "files in", "files on"]
        ):
            folder = list_match.group(1).strip()
            if folder in ("files", "my files", "all files", ""):
                return ("list_files", None)
            return ("list_files", folder)

        # Create folder
        create_match = re.search(
            r"(?:create|make|new)\s+(?:a\s+)?(?:folder|directory|dir)\s+(?:called\s+|named\s+)?(.+?)(?:[!?.]|$)",
            lower,
            re.IGNORECASE,
        )
        if create_match:
            return ("create_folder", create_match.group(1).strip())

        # Delete / Remove
        delete_match = re.search(
            r"(?:delete|remove|erase)\s+(?:the\s+)?(?:file\s+|folder\s+)?(.+?)(?:[!?.]|$)",
            lower,
            re.IGNORECASE,
        )
        if delete_match:
            return ("delete_file", delete_match.group(1).strip())

        # Rename
        rename_match = re.search(
            r"rename\s+(?:the\s+)?(?:file\s+|folder\s+)?(.+?)\s+(?:to|as)\s+(.+?)(?:[!?.]|$)",
            lower,
            re.IGNORECASE,
        )
        if rename_match:
            return ("rename_file", f"{rename_match.group(1).strip()}|{rename_match.group(2).strip()}")

        # Copy
        copy_match = re.search(
            r"copy\s+(?:the\s+)?(?:file\s+)?(.+?)\s+(?:to|into)\s+(.+?)(?:[!?.]|$)",
            lower,
            re.IGNORECASE,
        )
        if copy_match:
            return ("copy_file", f"{copy_match.group(1).strip()}|{copy_match.group(2).strip()}")

        # Move
        move_match = re.search(
            r"move\s+(?:the\s+)?(?:file\s+)?(.+?)\s+(?:to|into)\s+(.+?)(?:[!?.]|$)",
            lower,
            re.IGNORECASE,
        )
        if move_match:
            return ("move_file", f"{move_match.group(1).strip()}|{move_match.group(2).strip()}")


        # --- Web search ---
        wsearch_match = re.search(
            r"(?:search\s+(?:for|on\s+google)?|google|look\s+up)\s+(.+?)(?:[!?.]|$)",
            lower, re.IGNORECASE,
        )
        if wsearch_match:
            return ("web_search", wsearch_match.group(1).strip())

        # --- Type text ---
        type_match = re.search(
            r"(?:type|write|input)\s+(?:out\s+)?['\"]?(.+?)['\"]?(?:[!?.]|$)",
            lower, re.IGNORECASE,
        )
        if type_match:
            return ("type_text", type_match.group(1).strip())

        # --- Clipboard copy ---
        clip_match = re.search(
            r"(?:copy|clipboard)\s+(?:this\s+)?(?:to\s+clipboard[:\s]*)?['\"]?(.+?)['\"]?(?:[!?.]|$)",
            lower, re.IGNORECASE,
        )
        if clip_match:
            return ("clipboard_copy", clip_match.group(1).strip())

        # --- Media control ---
        media_match = re.search(
            r"(?:(next|skip)\s+(?:song|track|music))"
            r"|((?:previous|prev|back)\s+(?:song|track))"
            r"|(pause\s+(?:music|song|media|playback|video))"
            r"|((?:play|resume)\s+(?:music|song|media|playback))"
            r"|(stop\s+(?:music|song|media))",
            lower, re.IGNORECASE,
        )
        if media_match:
            if media_match.group(1):
                return ("media_control", "next")
            if media_match.group(2):
                return ("media_control", "previous")
            if media_match.group(3):
                return ("media_control", "pause")
            if media_match.group(4):
                return ("media_control", "play")
            if media_match.group(5):
                return ("media_control", "stop")

        # --- Timer ---
        timer_match = re.search(
            r"(?:set\s+(?:a\s+)?)?(?:timer|alarm|reminder)\s+(?:for\s+)?(?:(\d+)\s*(?:hour|hr)s?)?\s*(?:(\d+)\s*min(?:ute)?s?)?\s*(?:(\d+)\s*sec(?:ond)?s?)?",
            lower, re.IGNORECASE,
        )
        if timer_match and any(timer_match.groups()):
            hrs  = int(timer_match.group(1) or 0)
            mins = int(timer_match.group(2) or 0)
            secs = int(timer_match.group(3) or 0)
            total = hrs * 3600 + mins * 60 + secs
            if total > 0:
                return ("set_timer", str(total))

        # --- Email ---
        email_trigger = re.search(
            r"(?:send\s+(?:an?\s+)?(?:email|mail|e-mail)|email|mail)\s+(?:to\s+)?(.+)",
            lower, re.IGNORECASE,
        )
        if email_trigger:
            payload = email_trigger.group(1).strip()
            
            # Check for "subject X body Y" or "subject X saying Y"
            subj_match = re.search(r"(.*?)\s*(?:with\s+)?subject\s+(.+?)\s+(?:and\s+)?(?:body|saying|message)\s+(.+)", payload, re.IGNORECASE)
            # Check for just "saying Y" or "with body Y"
            body_match = re.search(r"(.*?)\s+(?:saying|with\s+(?:body|message)|body)\s+(.+)", payload, re.IGNORECASE)
            
            if subj_match:
                to_addr = subj_match.group(1).strip()
                subject = subj_match.group(2).strip()
                body = subj_match.group(3).strip()
            elif body_match:
                to_addr = body_match.group(1).strip()
                subject = "Message from Phase-5"
                body = body_match.group(2).strip()
            else:
                to_addr = payload
                subject = "Message from Phase-5"
                body = ""
                
            if to_addr:
                # remove stray 'to ' if present
                to_addr = re.sub(r"^to\s+", "", to_addr, flags=re.IGNORECASE).strip()
                return ("email", f"{to_addr}|{subject}|{body}")

        # --- WhatsApp ---
        # Two-step: strip command prefix, then split on 'saying/with/that says'
        wa_trigger = re.search(
            r"(?:whatsapp|wa|send\s+(?:a\s+)?(?:whatsapp|wa)?\s*(?:message|msg)?\s*(?:to)?)\s+(.+)",
            lower, re.IGNORECASE,
        )
        if wa_trigger:
            payload = wa_trigger.group(1).strip()
            split_parts = re.split(
                r"\s+(?:saying|with\s+message|that\s+says|with)\s+",
                payload, maxsplit=1, flags=re.IGNORECASE
            )
            contact = split_parts[0].strip()
            msg = split_parts[1].strip() if len(split_parts) > 1 else ""
            contact = re.sub(r'^to\s+', '', contact, flags=re.IGNORECASE).strip()
            if contact:
                return ("whatsapp", f"{contact}|{msg}")

        return ("chat", None)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    @staticmethod
    def execute_open(app_name: str) -> str:
        """Try to launch *app_name* on the host system.

        Priority:
        1. Start Menu Shortcut (most reliable for installed apps)
        2. Hardcoded Alias (calc, notepad, etc.)
        3. Direct execution (PATH)
        """
        # 1. Search Start Menu first (with fuzzy name matching for typos)
        shortcut_path = CommandHandler._find_in_start_menu(app_name)
        if shortcut_path:
            try:
                os.startfile(shortcut_path)  # type: ignore[attr-defined]
                return f"✅ Found and opened **{os.path.basename(shortcut_path)[:-4]}**."
            except OSError as exc:
                logger.error("Failed to launch shortcut %s: %s", shortcut_path, exc)

        # 2. Check aliases — exact first, then fuzzy
        a_lower = app_name.lower()
        resolved = APP_ALIASES.get(a_lower)
        if not resolved:
            # Fuzzy match against known alias keys
            close = difflib.get_close_matches(a_lower, APP_ALIASES.keys(), n=1, cutoff=0.72)
            if close:
                resolved = APP_ALIASES[close[0]]
                logger.debug("Fuzzy alias: '%s' -> '%s'", app_name, close[0])
        if not resolved:
            resolved = app_name

        try:
            # os.startfile works well on Windows (handles PATH + registered apps)
            os.startfile(resolved)  # type: ignore[attr-defined]
            return f"✅ Opened **{app_name}**."
        except OSError:
            pass

        # 3. Fallback: Check if it's in PATH using shutil.which
        # This prevents false positives where Popen(..., shell=True) succeeds but does nothing.
        if shutil.which(resolved):
            try:
                subprocess.Popen(
                    resolved,
                    shell=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return f"✅ Opened **{app_name}**."
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to launch '%s': %s", resolved, exc)

        # 4. Fallback: Search for UWP/Store apps (e.g. Telegram Desktop, Netflix)
        uwp_id = CommandHandler._find_uwp_app(app_name)
        if uwp_id:
            try:
                # Launch UWP app via explorer.exe shell:AppsFolder\<AppID>
                subprocess.run(
                    f"explorer.exe shell:AppsFolder\\{uwp_id}",
                    shell=True,
                    timeout=5
                )
                return f"✅ Found and opened **{app_name}** (Store App)."
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to launch UWP app %s: %s", uwp_id, exc)

        return f"⚠️ Could not find or open **{app_name}**."

    @staticmethod
    def _find_uwp_app(app_name: str) -> Optional[str]:
        """Find the AppUserModelId for a Windows Store app using PowerShell."""
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-Command",
                f"Get-StartApps | Where-Object {{ $_.Name -like '*{app_name}*' }} | Select-Object -First 1 -ExpandProperty AppID"
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=0x08000000 if os.name == "nt" else 0
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:  # noqa: BLE001
            pass
        return None

    @staticmethod
    def _find_in_start_menu(app_name: str) -> Optional[str]:
        """Recursively search for a matching .lnk file in Start Menu folders."""
        search_term = app_name.lower()
        
        # Windows Start Menu locations (handle missing env vars gracefully)
        start_menu_paths = []
        if "APPDATA" in os.environ:
            start_menu_paths.append(os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs"))
        if "ProgramData" in os.environ:
            start_menu_paths.append(os.path.join(os.environ["ProgramData"], "Microsoft", "Windows", "Start Menu", "Programs"))

        best_path: str | None = None
        best_score: int = 999

        for root_path in start_menu_paths:
            if not os.path.exists(root_path):
                continue
                
            for dirpath, _, filenames in os.walk(root_path):
                for filename in filenames:
                    # Check for .lnk extension safely
                    if len(filename) < 5 or not filename.lower().endswith(".lnk"):
                        continue
                    
                    # Convert filename (str) to lowercase name without extension
                    name = os.path.splitext(str(filename))[0].lower()
                    
                    # 1. Exact match
                    if name == search_term:
                        return os.path.join(dirpath, filename)
                    
                    # 2. Fuzzy match
                    if search_term in name:
                        # Prefer shorter matches (e.g. "Chrome" over "Google Chrome Canary")
                        score = len(name) - len(search_term)
                        if best_path is None or score < best_score:
                            best_path = os.path.join(dirpath, filename)
                            best_score = score
        
        return best_path
