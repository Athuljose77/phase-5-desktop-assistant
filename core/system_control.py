"""
Phase-5 — System Control
Handles volume, brightness, screenshots, and power actions.
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import webbrowser
from datetime import datetime
from typing import Optional

# 3rd party
import psutil  # type: ignore[import-not-found]
import pyautogui  # type: ignore[import-not-found]
import screen_brightness_control as sbc  # type: ignore[import-not-found]
from comtypes import CLSCTX_ALL  # type: ignore[import-not-found]
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)

# Output directory for screenshots
SCREENSHOT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "screenshots",
)


class SystemControl:
    """Interface for controlling Windows system settings."""

    # ------------------------------------------------------------------
    # Volume
    # ------------------------------------------------------------------

    @staticmethod
    def set_volume(level: int) -> str:
        """Set master volume to *level* (0-100)."""
        level = max(0, min(100, level))
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.EndpointVolume
            
            # Use scalar volume (0.0 to 1.0)
            scalar = level / 100.0
            interface.SetMasterVolumeLevelScalar(scalar, None)
            
            # Unmute if muted (optional, but good UX)
            if interface.GetMute():
                interface.SetMute(0, None)
                
            return f"🔊 Volume set to **{level}%**."
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to set volume: %s", exc)
            return "⚠️ Could not set volume."

    @staticmethod
    def mute_volume() -> str:
        """Mute system audio."""
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.EndpointVolume
            interface.SetMute(1, None)
            return "🔇 System muted."
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to mute: %s", exc)
            return "⚠️ Could not mute audio."

    @staticmethod
    def unmute_volume() -> str:
        """Unmute system audio."""
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.EndpointVolume
            interface.SetMute(0, None)
            return "🔊 System unmuted."
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to unmute: %s", exc)
            return "⚠️ Could not unmute audio."

    # ------------------------------------------------------------------
    # Brightness
    # ------------------------------------------------------------------

    @staticmethod
    def set_brightness(level: int) -> str:
        """Set screen brightness to *level* (0-100)."""
        level = max(0, min(100, level))
        try:
            sbc.set_brightness(level)
            return f"☀️ Brightness set to **{level}%**."
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to set brightness: %s", exc)
            return "⚠️ Could not set brightness (monitor might not support DDC/CI)."

    # ------------------------------------------------------------------
    # Screenshot
    # ------------------------------------------------------------------

    @staticmethod
    def take_screenshot() -> str:
        """Capture the primary screen and save to the screenshots folder."""
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        path = os.path.join(SCREENSHOT_DIR, filename)

        try:
            screenshot = pyautogui.screenshot()
            screenshot.save(path)
            # Open the file/folder for the user? Maybe just return success.
            # Let's open the screenshot directly for valid feedback.
            os.startfile(path)  # type: ignore[attr-defined]
            return f"📸 Screenshot saved: **{filename}**"
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to take screenshot: %s", exc)
            return "⚠️ Could not take screenshot."

    @staticmethod
    def get_screenshot_path() -> Optional[str]:
        """Capture the primary screen and return the path without opening it (for Vision)."""
        temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "temp")
        os.makedirs(temp_dir, exist_ok=True)
        path = os.path.join(temp_dir, "vision_capture.png")

        try:
            screenshot = pyautogui.screenshot()
            screenshot.save(path)
            return path
        except Exception as exc:
            logger.error("Failed to capture screen for vision: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Power
    # ------------------------------------------------------------------

    @staticmethod
    def lock_screen() -> str:
        """Lock the workstation."""
        try:
            # Windows API call to lock
            import ctypes
            ctypes.windll.user32.LockWorkStation()  # type: ignore[attr-defined]
            return "🔒 Screen locked."
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to lock screen: %s", exc)
            return "⚠️ Could not lock screen."

    # ------------------------------------------------------------------
    # Process Management
    # ------------------------------------------------------------------

    @staticmethod
    def close_app(app_name: str) -> str:
        """Find and terminate processes matching *app_name* safely."""
        # Clean input
        app_name = app_name.strip().lower()
        if len(app_name) < 3:
            return f"⚠️ Name '**{app_name}**' is too short to safely close apps."

        killed_count = 0
        
        # Mapping for common user-friendly names to actual process names
        # (Add common overrides here as needed)
        aliases = {
            "calculator": "calculatorapp",
            "vscode": "code",
            "chrome": "chrome",
            "notepad": "notepad",
            "spotify": "spotify",
        }
        target = aliases.get(app_name, app_name)

        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    p_name = proc.info['name'].lower()
                    
                    # Check for exact matches (e.g. "code" vs "code.exe")
                    # We avoid partial matching (e.g. "sys" in "system")
                    if p_name == target or p_name == f"{target}.exe":
                        proc.kill()
                        killed_count += 1  # type: ignore[operator]
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            if killed_count > 0:
                return f"🛑 Closed {killed_count} process(es) matching **{app_name}**."
            else:
                return f"⚠️ Could not find running app: **{app_name}** (process: {target})."

        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to close app %s: %s", app_name, exc)
            return f"⚠️ Error closing **{app_name}**: {exc}"

    # ------------------------------------------------------------------
    # Email
    # ------------------------------------------------------------------

    @staticmethod
    def send_email(to: str = "", subject: str = "", body: str = "") -> str:
        """Send an email via Gmail SMTP if credentials are set, else open mailto: link.

        Requires GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env.
        Get an App Password at: myaccount.google.com/apppasswords
        """
        from pathlib import Path

        # Load credentials from .env
        gmail_addr = ""
        gmail_pass = ""
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("GMAIL_ADDRESS="):
                    gmail_addr = line.split("=", 1)[1].strip()
                elif line.startswith("GMAIL_APP_PASSWORD="):
                    gmail_pass = line.split("=", 1)[1].strip()

        # ── SMTP send (if credentials configured) ──────────────────────
        if gmail_addr and gmail_pass and to:
            import smtplib
            from email.mime.text import MIMEText

            msg = MIMEText(body or "(no body)")
            msg["Subject"] = subject or "(no subject)"
            msg["From"] = gmail_addr
            msg["To"] = to
            try:
                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                    server.login(gmail_addr, gmail_pass)
                    server.sendmail(gmail_addr, [to], msg.as_string())
                return f"📧 Email sent to **{to}** — subject: *{subject or '(no subject)'}*"
            except smtplib.SMTPAuthenticationError:
                return (
                    "⚠️ Gmail authentication failed. Check your App Password in `.env` "
                    "(GMAIL_APP_PASSWORD). Get one at myaccount.google.com/apppasswords"
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("SMTP send failed: %s", exc)
                return f"⚠️ Could not send email: {exc}"

        # ── Fallback: open Gmail compose in browser (most reliable) ──────────
        import urllib.parse
        # Gmail compose URL — opens with To, Subject, Body all pre-filled
        gmail_compose = (
            "https://mail.google.com/mail/?view=cm"
            f"&to={urllib.parse.quote(to)}"
            f"&su={urllib.parse.quote(subject)}"
            f"&body={urllib.parse.quote(body)}"
        )
        try:
            webbrowser.open(gmail_compose)
            hint = " Add GMAIL credentials to .env to send without clicking!" if not gmail_addr else ""
            return f"📧 Gmail compose opened — to: **{to or '?'}**, subject: *{subject or '(none)'}*.{hint}"
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to open Gmail compose: %s", exc)
            return "⚠️ Could not open Gmail."


    # ------------------------------------------------------------------
    # Web Search
    # ------------------------------------------------------------------

    @staticmethod
    def web_search(query: str) -> str:
        """Open browser with a Google search for *query*."""
        import urllib.parse
        url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
        try:
            webbrowser.open(url)
            return f"🔍 Searching Google for **{query}**."
        except Exception as exc:  # noqa: BLE001
            logger.error("Web search failed: %s", exc)
            return "⚠️ Could not open browser."

    # ------------------------------------------------------------------
    # Keyboard / Typing
    # ------------------------------------------------------------------

    @staticmethod
    def type_text(text: str) -> str:
        """Type *text* into the currently focused window using pyautogui."""
        import time as _time
        try:
            _time.sleep(0.4)  # brief delay so window focus is stable
            pyautogui.write(text, interval=0.03)
            return f"⌨️ Typed: **{text[:60]}{'...' if len(text) > 60 else ''}**"
        except Exception as exc:  # noqa: BLE001
            logger.error("type_text failed: %s", exc)
            return "⚠️ Could not type text."

    @staticmethod
    def press_key(key: str) -> str:
        """Press a keyboard key or shortcut (e.g. 'enter', 'ctrl+c')."""
        try:
            if "+" in key:
                keys = [k.strip() for k in key.split("+")]
                pyautogui.hotkey(*keys)
            else:
                pyautogui.press(key.strip())
            return f"⌨️ Pressed **{key}**."
        except Exception as exc:  # noqa: BLE001
            logger.error("press_key failed: %s", exc)
            return "⚠️ Could not press key."

    # ------------------------------------------------------------------
    # Clipboard
    # ------------------------------------------------------------------

    @staticmethod
    def clipboard_copy(text: str) -> str:
        """Copy *text* to the system clipboard."""
        try:
            import tkinter as tk  # built-in
            root = tk.Tk()
            root.withdraw()
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update()
            root.after(500, root.destroy)
            root.mainloop()
            return f"📋 Copied to clipboard: **{text[:60]}{'...' if len(text) > 60 else ''}**"
        except Exception as exc:  # noqa: BLE001
            logger.error("clipboard_copy failed: %s", exc)
            return "⚠️ Could not copy to clipboard."

    # ------------------------------------------------------------------
    # Media Controls
    # ------------------------------------------------------------------

    _MEDIA_KEYS = {
        "play": "playpause",
        "pause": "playpause",
        "stop": "stop",
        "next": "nexttrack",
        "previous": "prevtrack",
        "prev": "prevtrack",
        "back": "prevtrack",
        "forward": "nexttrack",
        "mute_media": "volumemute",
        "volume_up": "volumeup",
        "volume_down": "volumedown",
    }

    @staticmethod
    def media_control(action: str) -> str:
        """Send a media key press for *action* (play/pause/next/previous/stop)."""
        action = action.strip().lower()
        key = SystemControl._MEDIA_KEYS.get(action)
        if not key:
            return f"⚠️ Unknown media action: **{action}**. Try: play, pause, next, previous, stop."
        try:
            pyautogui.press(key)
            emoji = {"playpause": "⏯", "stop": "⏹", "nexttrack": "⏭", "prevtrack": "⏮",
                     "volumemute": "🔇", "volumeup": "🔊", "volumedown": "🔉"}.get(key, "🎵")
            return f"{emoji} Media: **{action}**."
        except Exception as exc:  # noqa: BLE001
            logger.error("media_control failed: %s", exc)
            return "⚠️ Could not send media key."

    # ------------------------------------------------------------------
    # Timer / Reminder
    # ------------------------------------------------------------------

    @staticmethod
    def set_timer(seconds: int, label: str = "Timer") -> str:
        """Start a background countdown and show a Windows toast notification."""
        import threading

        def _notify() -> None:
            try:
                subprocess.Popen(
                    [
                        "powershell", "-Command",
                        f"[void][Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms');"
                        f"$n = New-Object System.Windows.Forms.NotifyIcon;"
                        f"$n.Icon = [System.Drawing.SystemIcons]::Information;"
                        f"$n.Visible = $true;"
                        f"$n.ShowBalloonTip(5000, '⚡ Phase-5 Timer', '{label} is done!', "
                        f"[System.Windows.Forms.ToolTipIcon]::Info);"
                        f"Start-Sleep -Seconds 6;"
                        f"$n.Dispose()",
                    ],
                    shell=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception as exc:
                logger.error("Timer notification failed: %s", exc)

        threading.Timer(seconds, _notify).start()
        mins, secs = divmod(seconds, 60)
        time_str = f"{mins}m {secs}s" if mins else f"{secs}s"
        return f"⏱️ Timer set for **{time_str}** — I'll notify you when done!"

    # ------------------------------------------------------------------
    # Email
    # ------------------------------------------------------------------

    @staticmethod
    def send_email(to: str, subject: str = "Message from Phase-5", body: str = "") -> str:
        """Open Gmail compose in a browser with pre-filled To/Subject/Body.
        Shows a dialog asking which browser to use and which Gmail account.
        """
        import urllib.parse
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QLabel,
            QPushButton, QComboBox, QSpinBox, QDialogButtonBox,
        )
        from PyQt6.QtCore import Qt

        # ── Detect installed browsers ─────────────────────────────────
        BROWSER_PATHS: dict[str, list[str]] = {
            "Microsoft Edge": [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            ],
            "Google Chrome": [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ],
            "Brave": [
                r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
            ],
        }

        available: dict[str, str] = {}  # name → exe path
        for name, paths in BROWSER_PATHS.items():
            for p in paths:
                if os.path.exists(p):
                    available[name] = p
                    break

        if not available:
            available["Default Browser"] = ""   # fallback: system default

        # ── Build Gmail compose URL ───────────────────────────────────
        def _make_url(account_idx: int) -> str:
            params = urllib.parse.urlencode({
                "view": "cm",
                "to": to,
                "su": subject,
                "body": body,
            })
            return f"https://mail.google.com/mail/u/{account_idx}/?{params}"

        # ── Show dialog ───────────────────────────────────────────────
        result_holder: dict[str, object] = {}

        class EmailDialog(QDialog):
            def __init__(self) -> None:
                super().__init__()
                self.setWindowTitle("📧 Open Gmail Compose")
                self.setMinimumWidth(360)
                layout = QVBoxLayout(self)

                layout.addWidget(QLabel(f"<b>To:</b> {to}"))
                layout.addWidget(QLabel(f"<b>Subject:</b> {subject}"))
                layout.addWidget(QLabel(f"<b>Body:</b> {body[:80]}{'…' if len(body)>80 else ''}"))
                layout.addWidget(QLabel(""))

                # Browser picker
                browser_row = QHBoxLayout()
                browser_row.addWidget(QLabel("Browser:"))
                self.browser_combo = QComboBox()
                for name in available:
                    self.browser_combo.addItem(name)
                browser_row.addWidget(self.browser_combo)
                layout.addLayout(browser_row)

                # Account index
                acc_row = QHBoxLayout()
                acc_row.addWidget(QLabel("Gmail account (0 = first, 1 = second …):"))
                self.acc_spin = QSpinBox()
                self.acc_spin.setRange(0, 9)
                self.acc_spin.setValue(0)
                acc_row.addWidget(self.acc_spin)
                layout.addLayout(acc_row)

                # Buttons
                btns = QDialogButtonBox(
                    QDialogButtonBox.StandardButton.Ok |
                    QDialogButtonBox.StandardButton.Cancel
                )
                btns.accepted.connect(self.accept)
                btns.rejected.connect(self.reject)
                layout.addWidget(btns)

            def accept(self) -> None:
                result_holder["browser"] = self.browser_combo.currentText()
                result_holder["account"] = self.acc_spin.value()
                super().accept()

        dlg = EmailDialog()
        dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return "📧 Email compose cancelled."

        browser_name = str(result_holder["browser"])
        account_idx  = int(str(result_holder["account"]))
        url = _make_url(account_idx)
        exe = available.get(browser_name, "")

        try:
            if exe:
                proc = subprocess.Popen([exe, url])
            else:
                import webbrowser
                webbrowser.open(url)
                
            # Wait for browser to load Gmail compose, then press Ctrl+Enter
            import time as _time
            import pyautogui as _ag
            import win32gui as _w32
            import ctypes as _ct
            
            _time.sleep(6.0)  # Wait 6 seconds for page to load fully
            
            # Find the active browser window and bring it to front
            hwnd = _w32.GetForegroundWindow()
            if hwnd:
                try:
                    _w32.ShowWindow(hwnd, 9) # SW_RESTORE
                    _ct.windll.user32.SetForegroundWindow(hwnd)
                except Exception:
                    pass
            _time.sleep(0.5)
            
            # Press Ctrl + Enter to send reliably
            _ag.hotkey("ctrl", "enter")
            
            return (
                f"📧 Successfully drafted and sent email via **{browser_name}** "
                f"(account #{account_idx}) for **{to}**."
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to open browser for Gmail: %s", exc)
            return f"⚠️ Could not open browser: {exc}"

    # ------------------------------------------------------------------
    # WhatsApp
    # ------------------------------------------------------------------

    @staticmethod
    def whatsapp_message(contact: str, message: str = "") -> str:
        """Send a WhatsApp message via desktop app automation."""
        import time as _time
        import win32gui as _w32
        import win32con as _w32c
        import win32api as _w32a
        import ctypes as _ct

        if not message:
            message = "Hello!"

        digits_only = contact.replace("+", "").replace(" ", "").replace("-", "")
        is_phone = digits_only.isdigit() and len(digits_only) >= 10
        search_term = digits_only if is_phone else contact
        label = f"+{digits_only}" if is_phone else contact

        def _activate(hwnd: int) -> None:
            """Force a window to the foreground reliably."""
            # Allow any process to call SetForegroundWindow
            _ct.windll.user32.AllowSetForegroundWindow(-1)
            _w32.ShowWindow(hwnd, _w32c.SW_RESTORE)
            _ct.windll.user32.SetForegroundWindow(hwnd)

        try:
            # ── 1. Find WhatsApp window (it's likely already running) ─────
            def _find_wa_hwnd() -> int | None:
                # Try exact title match first
                hwnd = _w32.FindWindow(None, "WhatsApp")
                if hwnd and _w32.IsWindowVisible(hwnd):
                    return hwnd
                # Fall back to substring search (catches "WhatsApp - ...")
                found = None
                def _enum(h, _):
                    nonlocal found
                    t = _w32.GetWindowText(h)
                    if t and "WhatsApp" in t and _w32.IsWindowVisible(h):
                        found = h
                _w32.EnumWindows(_enum, None)
                return found

            wa_hwnd = _find_wa_hwnd()

            # 2. Only launch if WhatsApp is not running ─────────────────
            if not wa_hwnd:
                subprocess.Popen(
                    ["cmd", "/c", "start", "", "whatsapp://"],
                    shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                # Wait up to 15 seconds for window to appear
                for _ in range(30):
                    _time.sleep(0.5)
                    wa_hwnd = _find_wa_hwnd()
                    if wa_hwnd:
                        break

            if not wa_hwnd:
                return "⚠️ WhatsApp window not found — please open WhatsApp first."

            # 3. Bring WhatsApp to the front ────────────────────────────
            _activate(wa_hwnd)
            _time.sleep(1.5)

            # 3. Open search and type the contact name ──────────────────
            # Ctrl+F opens the WhatsApp search panel
            _w32a.keybd_event(0x11, 0, 0, 0)          # Ctrl down
            _w32a.keybd_event(0x46, 0, 0, 0)          # F down
            _w32a.keybd_event(0x46, 0, 2, 0)          # F up (KEYEVENTF_KEYUP)
            _w32a.keybd_event(0x11, 0, 2, 0)          # Ctrl up
            _time.sleep(1.5)

            # Type the contact name one character at a time
            for ch in search_term:
                vk = _w32a.VkKeyScan(ch)
                _w32a.keybd_event(vk & 0xFF, 0, 0, 0)
                _w32a.keybd_event(vk & 0xFF, 0, 2, 0)
                _time.sleep(0.07)
            _time.sleep(2.5)  # wait for search results

            # ── 4. Navigate results and open the chat ─────────────────────
            _w32a.keybd_event(0x28, 0, 0, 0)  # DOWN arrow
            _w32a.keybd_event(0x28, 0, 2, 0)
            _time.sleep(0.5)
            _w32a.keybd_event(0x0D, 0, 0, 0)  # ENTER
            _w32a.keybd_event(0x0D, 0, 2, 0)
            _time.sleep(2.5)  # wait for chat to load

            # ── 5. Click the message input (win32api mouse click) ─────────
            # Re-activate window to ensure it has focus after chat opened
            _activate(wa_hwnd)
            _time.sleep(0.8)

            left, top, right, bottom = _w32.GetWindowRect(wa_hwnd)
            w = right - left
            # Message input: right 2/3 of window, 50px above bottom
            msg_x = left + (w // 2) + (w // 4)
            msg_y = bottom - 50
            # Move mouse and click using win32api (lower-level than pyautogui)
            _w32a.SetCursorPos((msg_x, msg_y))
            _time.sleep(0.3)
            _w32a.mouse_event(0x0002, 0, 0, 0, 0)   # MOUSEEVENTF_LEFTDOWN
            _w32a.mouse_event(0x0004, 0, 0, 0, 0)   # MOUSEEVENTF_LEFTUP
            _time.sleep(0.5)

            # ── 7. Type the message ───────────────────────────────────────
            for ch in message:
                if ch == " ":
                    _w32a.keybd_event(0x20, 0, 0, 0)   # SPACE
                    _w32a.keybd_event(0x20, 0, 2, 0)
                else:
                    vk = _w32a.VkKeyScan(ch)
                    shift = (vk >> 8) & 1
                    if shift:
                        _w32a.keybd_event(0x10, 0, 0, 0)   # SHIFT down
                    _w32a.keybd_event(vk & 0xFF, 0, 0, 0)
                    _w32a.keybd_event(vk & 0xFF, 0, 2, 0)
                    if shift:
                        _w32a.keybd_event(0x10, 0, 2, 0)   # SHIFT up
                _time.sleep(0.05)

            _time.sleep(0.4)

            # ── 8. Send with Enter ────────────────────────────────────────
            _w32a.keybd_event(0x0D, 0, 0, 0)
            _w32a.keybd_event(0x0D, 0, 2, 0)

            return f"\U0001f4ac WhatsApp message sent to **{label}**: *{message[:60]}*"

        except Exception as exc:  # noqa: BLE001
            logger.error("WhatsApp automation failed: %s", exc)
            return f"\u26a0\ufe0f WhatsApp failed: {exc}"

    @staticmethod
    def get_system_info() -> dict[str, str | int | float]:
        """Gather system hardware and OS details."""
        def format_bytes(size: int) -> str:
            # 1GB = 1024^3 bytes
            power = 2**30
            n = size / power
            return f"{n:.2f} GB"

        try:
            mem = psutil.virtual_memory()
            freq = psutil.cpu_freq()
            
            info = {
                "os": f"{platform.system()} {platform.release()} ({platform.version()})",
                "machine": platform.machine(),
                "processor": platform.processor(),
                "cpu_cores_physical": psutil.cpu_count(logical=False),
                "cpu_cores_logical": psutil.cpu_count(logical=True),
                "cpu_freq_current": f"{freq.current:.2f}Mhz" if freq else "Unknown",
                "cpu_freq_max": f"{freq.max:.2f}Mhz" if freq else "Unknown",
                "ram_total": format_bytes(mem.total),
                "ram_available": format_bytes(mem.available),
                "ram_percent_used": f"{mem.percent}%",
            }
            return info
        except Exception as exc:
            logger.error("Failed to get system info: %s", exc)
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # File Operations
    # ------------------------------------------------------------------

    # Common app aliases → executable paths for "open X in Y"
    FILE_APP_ALIASES: dict[str, list[str]] = {
        "vlc": [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
        ],
        "media player": ["wmplayer"],
        "notepad": ["notepad"],
        "notepad++": [
            r"C:\Program Files\Notepad++\notepad++.exe",
            r"C:\Program Files (x86)\Notepad++\notepad++.exe",
        ],
        "word": ["winword"],
        "excel": ["excel"],
        "chrome": ["chrome"],
        "firefox": ["firefox"],
        "edge": ["msedge"],
        "paint": ["mspaint"],
        "vscode": ["code"],
        "code": ["code"],
    }

    # Map generic words to file extensions for searching
    GENERIC_FILE_TYPES: dict[str, list[str]] = {
        "video": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"],
        "a video": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"],
        "movie": [".mp4", ".mkv", ".avi", ".mov", ".wmv"],
        "song": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
        "a song": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
        "music": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
        "photo": [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"],
        "a photo": [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"],
        "image": [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"],
        "picture": [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"],
        "document": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx"],
        "a document": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx"],
    }

    # Folders to search when user says "play song.mp3" without full path
    SEARCH_DIRS: list[str] = [
        os.path.join(os.path.expanduser("~"), "Desktop"),
        os.path.join(os.path.expanduser("~"), "Documents"),
        os.path.join(os.path.expanduser("~"), "Downloads"),
        os.path.join(os.path.expanduser("~"), "Videos"),
        os.path.join(os.path.expanduser("~"), "Music"),
        os.path.join(os.path.expanduser("~"), "Pictures"),
    ]

    @staticmethod
    def _resolve_app_path(app_name: str) -> Optional[str]:
        """Find the actual executable path for an app alias.

        Search order:
        1. Hardcoded aliases (FILE_APP_ALIASES)
        2. PATH lookup via `where`
        3. Start Menu shortcuts (.lnk files)
        """
        app_name = app_name.strip().lower()

        # 1. Check hardcoded aliases first
        candidates = SystemControl.FILE_APP_ALIASES.get(app_name, [])
        for candidate in candidates:
            if os.path.isabs(candidate) and os.path.exists(candidate):
                return candidate

        # 2. Try PATH lookup via `where`
        try:
            result = subprocess.run(
                f"where {app_name}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip().split("\n")[0]
        except Exception:
            pass

        # 3. Search Start Menu shortcuts for ANY installed app
        start_menu_paths = [
            os.path.join(
                os.environ.get("APPDATA", ""),
                "Microsoft", "Windows", "Start Menu", "Programs",
            ),
            r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
        ]

        for menu_path in start_menu_paths:
            if not os.path.isdir(menu_path):
                continue
            for dirpath, _, filenames in os.walk(menu_path):
                for filename in filenames:
                    if not filename.lower().endswith(".lnk"):
                        continue
                    name_no_ext = filename[:-4].lower()  # type: ignore[index]
                    if app_name in name_no_ext or name_no_ext in app_name:
                        shortcut_path = os.path.join(dirpath, filename)
                        # Try to resolve .lnk to actual exe path
                        exe_path = SystemControl._resolve_shortcut(shortcut_path)
                        if exe_path:
                            return exe_path
                        # Fallback: return the shortcut itself
                        return shortcut_path

        # 4. Last resort: return the name as-is
        return app_name

    @staticmethod
    def _resolve_shortcut(lnk_path: str) -> Optional[str]:
        """Resolve a Windows .lnk shortcut to its target exe path."""
        try:
            import win32com.client  # type: ignore[import-not-found]
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(lnk_path)
            target = shortcut.TargetPath
            if target and os.path.exists(target):
                return target
        except ImportError:
            # win32com not available, try PowerShell
            try:
                result = subprocess.run(
                    f'powershell -Command "(New-Object -ComObject WScript.Shell).CreateShortcut(\'{lnk_path}\').TargetPath"',
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                target = result.stdout.strip()
                if target and os.path.exists(target):
                    return target
            except Exception:
                pass
        except Exception:
            pass
        return None

    @staticmethod
    def open_file(filepath: str) -> str:
        """Open a file with its default application."""
        filepath = filepath.strip().strip('"').strip("'")

        # Check if it's a generic type like "a video"
        generic_exts = SystemControl.GENERIC_FILE_TYPES.get(filepath.lower())
        if generic_exts:
            found = SystemControl._search_by_extension(generic_exts)
            if found:
                filepath = found
            else:
                return f"⚠️ Could not find any {filepath} files in your folders."

        # If not an absolute path, try to find it
        elif not os.path.isabs(filepath):
            found = SystemControl.search_file(filepath)
            if found:
                filepath = found
            else:
                return f"⚠️ Could not find file: **{filepath}**"

        if not os.path.exists(filepath):
            return f"⚠️ File not found: **{filepath}**"

        try:
            os.startfile(filepath)  # type: ignore[attr-defined]
            return f"✅ Opened **{os.path.basename(filepath)}**."
        except Exception as exc:
            logger.error("Failed to open file %s: %s", filepath, exc)
            return f"⚠️ Could not open **{filepath}**: {exc}"

    @staticmethod
    def open_file_with_app(filepath: str, app_name: str) -> str:
        """Open a file using a specific application."""
        filepath = filepath.strip().strip('"').strip("'")

        # Resolve app to a real executable path
        app_exe = SystemControl._resolve_app_path(app_name)
        if not app_exe:
            return f"⚠️ Could not find application: **{app_name}**"

        # Check if it's a generic type like "a video"
        generic_exts = SystemControl.GENERIC_FILE_TYPES.get(filepath.lower())
        if generic_exts:
            found = SystemControl._search_by_extension(generic_exts)
            if found:
                filepath = found
            else:
                return f"⚠️ Could not find any {filepath} files in your folders."

        # If not an absolute path, try to find it
        elif not os.path.isabs(filepath):
            found = SystemControl.search_file(filepath)
            if found:
                filepath = found
            else:
                return f"⚠️ Could not find file: **{filepath}**"

        if not os.path.exists(filepath):
            return f"⚠️ File not found: **{filepath}**"

        try:
            subprocess.Popen(
                [app_exe, filepath],
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return f"✅ Opened **{os.path.basename(filepath)}** in **{app_name}**."
        except Exception as exc:
            logger.error("Failed to open %s with %s: %s", filepath, app_exe, exc)
            return f"⚠️ Could not open with **{app_name}**: {exc}"

    @staticmethod
    def _search_by_extension(extensions: list[str]) -> Optional[str]:
        """Search user directories for the first file matching any extension."""
        for search_dir in SystemControl.SEARCH_DIRS:
            if not os.path.isdir(search_dir):
                continue
            for dirpath, _, filenames in os.walk(search_dir):
                for f in filenames:
                    if any(f.lower().endswith(ext) for ext in extensions):
                        return os.path.join(dirpath, f)
        return None

    @staticmethod
    def search_file(filename: str) -> Optional[str]:
        """Search common user directories for a file by name.
        Returns the full path if found, or None.
        """
        filename_lower = filename.strip().lower()
        for search_dir in SystemControl.SEARCH_DIRS:
            if not os.path.isdir(search_dir):
                continue
            for dirpath, _, filenames in os.walk(search_dir):
                for f in filenames:
                    if f.lower() == filename_lower:
                        return os.path.join(dirpath, f)
                    # Also try partial match for "video" matching "video.mp4"
                    if filename_lower in f.lower():
                        return os.path.join(dirpath, f)
        return None

    # ------------------------------------------------------------------
    # File Management
    # ------------------------------------------------------------------

    @staticmethod
    def list_files(path: Optional[str] = None) -> str:
        """List files and folders in a directory.

        Defaults to the user's Desktop if no path is given.
        """
        if not path:
            path = os.path.join(os.path.expanduser("~"), "Desktop")
        path = os.path.expanduser(path)

        # Resolve common folder names to full paths
        _FOLDER_ALIASES: dict[str, str] = {
            "desktop": os.path.join(os.path.expanduser("~"), "Desktop"),
            "documents": os.path.join(os.path.expanduser("~"), "Documents"),
            "downloads": os.path.join(os.path.expanduser("~"), "Downloads"),
            "pictures": os.path.join(os.path.expanduser("~"), "Pictures"),
            "music": os.path.join(os.path.expanduser("~"), "Music"),
            "videos": os.path.join(os.path.expanduser("~"), "Videos"),
        }
        if path.lower() in _FOLDER_ALIASES:
            path = _FOLDER_ALIASES[path.lower()]

        if not os.path.isdir(path):
            return f"⚠️ Directory not found: **{path}**"

        try:
            entries = sorted(os.listdir(path))
        except PermissionError:
            return f"⚠️ Permission denied: **{path}**"

        if not entries:
            return f"📂 **{path}** is empty."

        lines: list[str] = [f"📂 **{path}** ({len(entries)} items):\n"]
        for entry in entries:
            full_path = os.path.join(path, entry)
            if os.path.isdir(full_path):
                lines.append(f"  📁 {entry}/")
            else:
                size = os.path.getsize(full_path)
                lines.append(f"  📄 {entry}  ({SystemControl._format_size(size)})")
        return "\n".join(lines)

    @staticmethod
    def _format_size(size: int) -> str:
        """Format file size in human-readable units."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}" if unit != "B" else f"{size} B"
            size /= 1024  # type: ignore[assignment]
        return f"{size:.1f} TB"

    @staticmethod
    def create_folder(path: str) -> str:
        """Create a new directory (with parents if needed)."""
        path = os.path.expanduser(path)

        # If just a name like "projects", create on Desktop
        if os.sep not in path and "/" not in path:
            path = os.path.join(os.path.expanduser("~"), "Desktop", path)

        if os.path.exists(path):
            return f"⚠️ Already exists: **{path}**"

        try:
            os.makedirs(path, exist_ok=True)
            return f"📁 Created folder: **{path}**"
        except OSError as exc:
            return f"⚠️ Could not create folder: {exc}"

    @staticmethod
    def delete_file(path: str) -> str:
        """Delete a file or empty folder."""
        path = os.path.expanduser(path)

        # Search for the file if not an absolute path
        if not os.path.exists(path):
            found = SystemControl.search_file(os.path.basename(path))
            if found:
                path = found
            else:
                return f"⚠️ Not found: **{path}**"

        try:
            if os.path.isdir(path):
                os.rmdir(path)
                return f"🗑️ Deleted folder: **{path}**"
            else:
                os.remove(path)
                return f"🗑️ Deleted: **{path}**"
        except OSError as exc:
            return f"⚠️ Could not delete: {exc}"

    @staticmethod
    def rename_file(old_path: str, new_name: str) -> str:
        """Rename a file or folder."""
        old_path = os.path.expanduser(old_path)

        if not os.path.exists(old_path):
            found = SystemControl.search_file(os.path.basename(old_path))
            if found:
                old_path = found
            else:
                return f"⚠️ Not found: **{old_path}**"

        # If new_name is just a name (no path), keep in the same directory
        if os.sep not in new_name and "/" not in new_name:
            new_path = os.path.join(os.path.dirname(old_path), new_name)
        else:
            new_path = os.path.expanduser(new_name)

        try:
            os.rename(old_path, new_path)
            return f"✏️ Renamed **{os.path.basename(old_path)}** → **{os.path.basename(new_path)}**"
        except OSError as exc:
            return f"⚠️ Could not rename: {exc}"

    @staticmethod
    def copy_file(src: str, dest: str) -> str:
        """Copy a file to a destination."""
        import shutil
        src = os.path.expanduser(src)
        dest = os.path.expanduser(dest)

        if not os.path.exists(src):
            found = SystemControl.search_file(os.path.basename(src))
            if found:
                src = found
            else:
                return f"⚠️ Source not found: **{src}**"

        # If dest is a folder name alias, resolve it
        _FOLDER_ALIASES: dict[str, str] = {
            "desktop": os.path.join(os.path.expanduser("~"), "Desktop"),
            "documents": os.path.join(os.path.expanduser("~"), "Documents"),
            "downloads": os.path.join(os.path.expanduser("~"), "Downloads"),
        }
        if dest.lower() in _FOLDER_ALIASES:
            dest = _FOLDER_ALIASES[dest.lower()]

        try:
            if os.path.isdir(dest):
                dest = os.path.join(dest, os.path.basename(src))
            shutil.copy2(src, dest)
            return f"📋 Copied **{os.path.basename(src)}** → **{dest}**"
        except OSError as exc:
            return f"⚠️ Could not copy: {exc}"

    @staticmethod
    def move_file(src: str, dest: str) -> str:
        """Move a file to a destination."""
        import shutil
        src = os.path.expanduser(src)
        dest = os.path.expanduser(dest)

        if not os.path.exists(src):
            found = SystemControl.search_file(os.path.basename(src))
            if found:
                src = found
            else:
                return f"⚠️ Source not found: **{src}**"

        _FOLDER_ALIASES: dict[str, str] = {
            "desktop": os.path.join(os.path.expanduser("~"), "Desktop"),
            "documents": os.path.join(os.path.expanduser("~"), "Documents"),
            "downloads": os.path.join(os.path.expanduser("~"), "Downloads"),
        }
        if dest.lower() in _FOLDER_ALIASES:
            dest = _FOLDER_ALIASES[dest.lower()]

        try:
            if os.path.isdir(dest):
                dest = os.path.join(dest, os.path.basename(src))
            shutil.move(src, dest)
            return f"📦 Moved **{os.path.basename(src)}** → **{dest}**"
        except OSError as exc:
            return f"⚠️ Could not move: {exc}"

    @staticmethod
    def file_info(path: str) -> str:
        """Get file/folder information."""
        path = os.path.expanduser(path)

        if not os.path.exists(path):
            found = SystemControl.search_file(os.path.basename(path))
            if found:
                path = found
            else:
                return f"⚠️ Not found: **{path}**"

        try:
            stat = os.stat(path)
            modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            created = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M")

            if os.path.isdir(path):
                count = len(os.listdir(path))
                return (
                    f"📁 **{os.path.basename(path)}**\n"
                    f"  Type: Folder\n"
                    f"  Items: {count}\n"
                    f"  Modified: {modified}\n"
                    f"  Created: {created}\n"
                    f"  Path: {path}"
                )
            else:
                return (
                    f"📄 **{os.path.basename(path)}**\n"
                    f"  Type: File\n"
                    f"  Size: {SystemControl._format_size(stat.st_size)}\n"
                    f"  Modified: {modified}\n"
                    f"  Created: {created}\n"
                    f"  Path: {path}"
                )
        except OSError as exc:
            return f"⚠️ Could not get info: {exc}"

    # ------------------------------------------------------------------
    # Power Management
    # ------------------------------------------------------------------

    @staticmethod
    def shutdown() -> str:
        """Shut down the computer (with 30s delay so user can cancel)."""
        try:
            subprocess.Popen("shutdown /s /t 30", shell=True)
            return "🔴 Shutting down in 30 seconds. Run `shutdown /a` to cancel."
        except Exception as exc:
            logger.error("Shutdown failed: %s", exc)
            return f"⚠️ Shutdown failed: {exc}"

    @staticmethod
    def restart() -> str:
        """Restart the computer (with 30s delay)."""
        try:
            subprocess.Popen("shutdown /r /t 30", shell=True)
            return "🔄 Restarting in 30 seconds. Run `shutdown /a` to cancel."
        except Exception as exc:
            logger.error("Restart failed: %s", exc)
            return f"⚠️ Restart failed: {exc}"

    @staticmethod
    def sleep() -> str:
        """Put the computer to sleep."""
        try:
            subprocess.Popen(
                "rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True
            )
            return "😴 Putting computer to sleep..."
        except Exception as exc:
            logger.error("Sleep failed: %s", exc)
            return f"⚠️ Sleep failed: {exc}"

    # ------------------------------------------------------------------
    # Network
    # ------------------------------------------------------------------

    @staticmethod
    def toggle_wifi(enable: bool) -> str:
        """Enable or disable WiFi adapter."""
        action = "enable" if enable else "disable"
        try:
            result = subprocess.run(
                f'netsh interface set interface "Wi-Fi" {action}',
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                emoji = "📶" if enable else "📴"
                return f"{emoji} WiFi **{action}d** successfully."
            else:
                return f"⚠️ Could not {action} WiFi. Try running as Administrator."
        except Exception as exc:
            logger.error("WiFi toggle failed: %s", exc)
            return f"⚠️ WiFi toggle failed: {exc}"

    # ------------------------------------------------------------------
    # URL Opening
    # ------------------------------------------------------------------

    @staticmethod
    def open_url(url: str, browser: Optional[str] = None) -> str:
        """Open a URL in the default or specified browser."""
        # Add https:// if no protocol
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        try:
            if browser:
                browser_lower = browser.lower()
                browser_map = {
                    "chrome": "chrome",
                    "firefox": "firefox",
                    "edge": "msedge",
                }
                browser_cmd = browser_map.get(browser_lower)
                if browser_cmd:
                    subprocess.Popen(
                        [browser_cmd, url],
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return f"🌐 Opened **{url}** in **{browser}**."
            # Default browser
            webbrowser.open(url)
            return f"🌐 Opened **{url}**."
        except Exception as exc:
            logger.error("Failed to open URL %s: %s", url, exc)
            return f"⚠️ Could not open URL: {exc}"
