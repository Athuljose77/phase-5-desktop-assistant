"""
Phase-5 — GUI
PyQt6 main window with a modern chat interface, animated typing indicator,
Markdown rendering, streaming response support, and background AI worker.
"""

from __future__ import annotations

import html
import re
import time
from typing import Optional

from PyQt6.QtCore import (  # type: ignore[import-not-found]
    QThread,
    QTimer,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import (  # type: ignore[import-not-found]
    QFont,
    QKeySequence,
    QShortcut,
)
from PyQt6.QtWidgets import (  # type: ignore[import-not-found]
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


# =====================================================================
# Worker Thread — runs AI generation off the main thread
# =====================================================================

class WorkerThread(QThread):
    """Runs ``generate_response`` on a background thread and
    emits the result via a signal so the GUI can update safely.

    Signals
    -------
    result_ready : str
        Emitted with the completed AI response text.
    mode_changed : str
        Emitted with ``"online"`` or ``"offline"`` when the mode is decided.
    """

    mode_changed = pyqtSignal(str)
    result_ready = pyqtSignal(str)

    def __init__(
        self,
        ai_handler,
        prompt: str,
        context: Optional[str] = None,
        image_path: Optional[str] = None,
        parent: Optional[QThread] = None,
    ) -> None:
        super().__init__(parent)  # type: ignore[call-arg]
        self._ai = ai_handler
        self._prompt = prompt
        self._context = context
        self._image_path = image_path
        self._start_time: float = 0

    def run(self) -> None:  # noqa: D401
        """Entry point for the thread — calls AI and emits result."""
        self._start_time = time.time()
        
        # Check if the AI handler accepts image_path (HybridAIHandler does)
        try:
             response = self._ai.generate_response(
                 prompt=self._prompt,
                 context=self._context,
                 on_mode_decided=lambda mode: self.mode_changed.emit(mode),
                 image_path=self._image_path,
             )
        except TypeError:
             # Fallback for old AIHandler that doesn't have image_path
             response = self._ai.generate_response(
                 self._prompt,
                 self._context,
                 on_mode_decided=lambda mode: self.mode_changed.emit(mode),
             )
        
        elapsed = time.time() - self._start_time
        # Attach metadata as a hidden suffix
        model_name = getattr(self._ai, '_current_mode', 'unknown')
        response += f"\n<!--META:{elapsed:.1f}s|{model_name}-->"
        self.result_ready.emit(response)


# =====================================================================
# Simple Markdown → HTML converter
# =====================================================================

def _md_to_html(text: str) -> str:
    """Convert basic Markdown to styled HTML for display.

    Supports: **bold**, *italic*, `code`, ```code blocks```,
    headings (#), bullet lists, and numbered lists.
    """
    # Escape HTML first
    text = html.escape(text)

    # Code blocks (``` ... ```)
    def _code_block(m):  # type: ignore[no-untyped-def]
        code = m.group(1).strip()
        return (
            '<div style="background-color:#1a1a2e; border-radius:8px; '
            'padding:12px 16px; margin:8px 0; font-family:Consolas,monospace; '
            f'font-size:13px; color:#e2e8f0; white-space:pre-wrap;">{code}</div>'
        )

    text = re.sub(r"```(?:\w+)?\n(.*?)```", _code_block, text, flags=re.DOTALL)

    # Inline code
    text = re.sub(
        r"`([^`]+)`",
        r'<span style="background-color:#1a1a2e; color:#a78bfa; '
        r'padding:2px 6px; border-radius:4px; font-family:Consolas,monospace; '
        r'font-size:13px;">\1</span>',
        text,
    )

    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)

    # Italic
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)

    # Headings (### > ## > #)
    text = re.sub(
        r"^### (.+)$",
        r'<div style="font-size:14px; font-weight:bold; color:#c4b5fd; '
        r'margin:10px 0 4px 0;">\1</div>',
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r"^## (.+)$",
        r'<div style="font-size:15px; font-weight:bold; color:#a78bfa; '
        r'margin:12px 0 4px 0;">\1</div>',
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r"^# (.+)$",
        r'<div style="font-size:16px; font-weight:bold; color:#8b5cf6; '
        r'margin:14px 0 6px 0;">\1</div>',
        text,
        flags=re.MULTILINE,
    )

    # Bullet lists (- item or * item)
    text = re.sub(
        r"^[\-\*] (.+)$",
        r'<div style="margin:2px 0 2px 16px;">• \1</div>',
        text,
        flags=re.MULTILINE,
    )

    # Numbered lists (1. item)
    def _numbered_list(m):  # type: ignore[no-untyped-def]
        return f'<div style="margin:2px 0 2px 16px;">{m.group(1)}. {m.group(2)}</div>'

    text = re.sub(r"^(\d+)\. (.+)$", _numbered_list, text, flags=re.MULTILINE)

    # Newlines → <br> (but not inside code blocks)
    text = text.replace("\n", "<br>")

    return text


# =====================================================================
# Animated Typing Indicator Widget
# =====================================================================

class TypingIndicator(QWidget):
    """A text-based animated typing indicator — reliably visible."""

    _FRAMES = [
        "⚡ Phase-5 is thinking",
        "⚡ Phase-5 is thinking <b style='color:#8b5cf6;'>.</b>",
        "⚡ Phase-5 is thinking <b style='color:#8b5cf6;'>..</b>",
        "⚡ Phase-5 is thinking <b style='color:#8b5cf6;'>...</b>",
    ]

    def __init__(self, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.setFixedHeight(36)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(44, 4, 44, 4)
        layout.setSpacing(0)

        self._label = QLabel(self._FRAMES[0])
        self._label.setFont(QFont("Segoe UI", 12))
        self._label.setStyleSheet("color: #8e8e8e; background-color: transparent;")
        self._label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self._label)
        layout.addStretch()

        self.setStyleSheet(
            "background-color: #0d0d14; "
            "border-top: 1px solid #1a1a2e;"
        )

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._tick = 0

    def start(self) -> None:
        """Start the animation."""
        self._tick = 0
        self._label.setText(self._FRAMES[0])
        self._timer.start(400)
        self.show()

    def stop(self) -> None:
        """Stop the animation and hide."""
        self._timer.stop()
        self.hide()

    def _animate(self) -> None:
        """Cycle through text frames."""
        self._tick += 1
        self._label.setText(self._FRAMES[self._tick % len(self._FRAMES)])


# =====================================================================
# Modern Dark Stylesheet
# =====================================================================

DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #1c1c1c;
}
QTextEdit {
    background-color: transparent;
    color: #e8e8e8;
    border: none;
    padding: 0px 20px;
    font-size: 14px;
    font-family: 'Segoe UI', 'Inter', sans-serif;
    line-height: 1.7;
    selection-background-color: #4c1d95;
}
QLineEdit {
    background-color: transparent;
    color: #e8e8e8;
    border: none;
    padding: 10px 4px;
    font-size: 14px;
    font-family: 'Segoe UI', 'Inter', sans-serif;
    selection-background-color: #4c1d95;
}
QLineEdit:focus { border: none; outline: none; }
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #3a3a3a;
    border-radius: 3px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


# =====================================================================
# Main Window
# =====================================================================

class VoiceWorkerThread(QThread):
    """Runs speech recognition in a background thread."""

    text_ready = pyqtSignal(str)
    error = pyqtSignal(str)

    def run(self) -> None:
        try:
            from core.voice_handler import listen  # type: ignore[import-not-found]
            result = listen(timeout=8, phrase_limit=15)
            if result:
                self.text_ready.emit(result)
            else:
                self.error.emit("No speech detected. Try again.")
        except RuntimeError as exc:
            # Descriptive errors from voice_handler
            self.error.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.error.emit(f"Voice error: {exc}")


class MainWindow(QMainWindow):
    """The primary Phase-5 chat window.

    Signals
    -------
    user_message : str
        Emitted when the user submits a message (Enter or Send click).
    voice_text : str
        Emitted when voice input is transcribed.
    """

    user_message = pyqtSignal(str)
    voice_text = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Phase-5")
        self.setMinimumSize(700, 500)
        self.resize(960, 680)
        self.setStyleSheet(DARK_STYLE)

        # Root layout
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Slim top bar ───────────────────────────────────────────────────────
        top_bar = QWidget()
        top_bar.setFixedHeight(40)
        top_bar.setStyleSheet("background-color:#1c1c1c;")
        tb_layout = QHBoxLayout(top_bar)
        tb_layout.setContentsMargins(20, 0, 20, 0)
        lbl = QLabel("⚡ Phase-5")
        lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl.setStyleSheet("color:#555; background:transparent;")
        tb_layout.addWidget(lbl)
        tb_layout.addStretch()
        self.mode_indicator = QLabel("🟠 offline")
        self.mode_indicator.setFont(QFont("Segoe UI", 10))
        self.mode_indicator.setStyleSheet("color:#888; background:transparent; padding:2px 10px;")
        tb_layout.addWidget(self.mode_indicator)
        root.addWidget(top_bar)

        # ── Content area (greeting + chat stacked) ──────────────────────────
        content = QWidget()
        content.setStyleSheet("background-color:#1c1c1c;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        root.addWidget(content, stretch=1)

        # Chat display (hidden initially)
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Segoe UI", 12))
        self.chat_display.setStyleSheet(
            "background:transparent; color:#e8e8e8; border:none; padding:24px 80px;"
        )
        self.chat_display.hide()
        content_layout.addWidget(self.chat_display, stretch=1)

        # Greeting headline (centered, shown when chat is empty)
        self._greeting_shown = True
        self._greeting_wrapper = QWidget()
        self._greeting_wrapper.setStyleSheet("background:transparent;")
        gw_layout = QVBoxLayout(self._greeting_wrapper)
        gw_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gw_layout.setContentsMargins(20, 0, 20, 40)
        self._greeting_label = QLabel("What can I help with?")
        self._greeting_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Normal))
        self._greeting_label.setStyleSheet("color:#e8e8e8; background:transparent;")
        self._greeting_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gw_layout.addWidget(self._greeting_label)
        content_layout.addStretch(1)
        content_layout.addWidget(self._greeting_wrapper)
        content_layout.addStretch(1)

        # Typing indicator
        self.typing_indicator = TypingIndicator()
        self.typing_indicator.hide()
        self.typing_indicator.setStyleSheet("background:#1c1c1c; border:none;")
        content_layout.addWidget(self.typing_indicator)

        # ── Floating pill input bar ─────────────────────────────────────────
        bar_wrapper = QWidget()
        bar_wrapper.setStyleSheet("background-color:#1c1c1c;")
        bar_outer = QHBoxLayout(bar_wrapper)
        bar_outer.setContentsMargins(60, 12, 60, 20)

        pill = QWidget()
        pill.setStyleSheet(
            "background-color:#2b2b2b;"
            "border-radius:26px;"
            "border:1px solid #3a3a3a;"
        )
        pill_layout = QHBoxLayout(pill)
        pill_layout.setContentsMargins(10, 6, 10, 6)
        pill_layout.setSpacing(4)

        # + button
        self._attach_btn = QPushButton("+")
        self._attach_btn.setFixedSize(36, 36)
        self._attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._attach_btn.setToolTip("Attach screenshot / file")
        self._attach_btn.setStyleSheet(
            "QPushButton{background:#3a3a3a;color:#bbb;border:none;"
            "border-radius:18px;font-size:18px;font-weight:normal;}"
            "QPushButton:hover{background:#4a4a4a;}"
        )
        pill_layout.addWidget(self._attach_btn)

        # Text field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask anything")
        self.input_field.setFont(QFont("Segoe UI", 13))
        self.input_field.setStyleSheet(
            "background:transparent;color:#e8e8e8;border:none;padding:6px 8px;"
        )
        pill_layout.addWidget(self.input_field, stretch=1)

        # Mic button
        self.mic_btn = QPushButton("🎙")
        self.mic_btn.setFixedSize(38, 38)
        self.mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mic_btn.setToolTip("Voice input (Ctrl+M)")
        self.mic_btn.setStyleSheet(
            "QPushButton{background:transparent;color:#bbb;border:none;"
            "border-radius:19px;font-size:15px;}"
            "QPushButton:hover{background:#3a3a3a;}"
        )
        pill_layout.addWidget(self.mic_btn)

        # TTS / waveform button
        self.tts_enabled = True
        self.tts_btn = QPushButton("⏺")
        self.tts_btn.setFixedSize(38, 38)
        self.tts_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tts_btn.setToolTip("Toggle voice response")
        self.tts_btn.setStyleSheet(
            "QPushButton{background:#505050;color:#e8e8e8;border:none;"
            "border-radius:19px;font-size:14px;}"
            "QPushButton:hover{background:#606060;}"
        )
        pill_layout.addWidget(self.tts_btn)

        bar_outer.addWidget(pill)
        root.addWidget(bar_wrapper)

        # Hidden send button (triggered by Enter)
        self.send_btn = QPushButton()
        self.send_btn.hide()

        # Voice worker
        self._voice_worker: VoiceWorkerThread | None = None
        self._is_listening = False

        # ── Connect signals ─────────────────────────────────────────────────
        self.send_btn.clicked.connect(self._on_send)
        self.input_field.returnPressed.connect(self._on_send)
        self.mic_btn.clicked.connect(self._on_mic)
        self.tts_btn.clicked.connect(self._on_toggle_tts)
        self._attach_btn.clicked.connect(self._on_attach)

        QShortcut(QKeySequence("Ctrl+Return"), self).activated.connect(self._on_send)
        QShortcut(QKeySequence("Ctrl+L"), self).activated.connect(self._clear_chat)
        QShortcut(QKeySequence("Ctrl+M"), self).activated.connect(self._on_mic)


    # ------------------------------------------------------------------
    # Mode indicator
    # ------------------------------------------------------------------

    def update_mode_indicator(self, mode: str) -> None:
        """Update the slim top-bar mode label."""
        if mode == "online":
            self.mode_indicator.setText("🟢 online")
            self.mode_indicator.setStyleSheet(
                "color:#4ade80; background:transparent; padding:2px 10px;"
            )
        else:
            self.mode_indicator.setText("🟠 offline")
            self.mode_indicator.setStyleSheet(
                "color:#fb923c; background:transparent; padding:2px 10px;"
            )

    def _hide_greeting(self) -> None:
        """Hide the centered greeting and show the chat display."""
        if self._greeting_shown:
            self._greeting_shown = False
            self._greeting_wrapper.hide()
            self.chat_display.show()

    # ------------------------------------------------------------------
    # Chat bubble helpers
    # ------------------------------------------------------------------

    def append_user(self, text: str) -> None:
        """Add a user bubble and hide the greeting headline."""
        self._hide_greeting()
        escaped = html.escape(text)
        bubble = (
            '<div style="text-align:right; margin:16px 0; padding:0 20px;">'
            '<span style="background-color:#7c3aed; color:#ffffff; '
            'padding:10px 18px; border-radius:18px 18px 4px 18px; '
            'display:inline-block; max-width:70%; text-align:left; '
            f'font-size:14px;">{escaped}</span></div>'
        )
        self.chat_display.append(bubble)
        self._scroll_to_bottom()

    def append_assistant(self, text: str, metadata: str = "") -> None:
        """Add an assistant bubble to the chat display.

        Parameters
        ----------
        text : str
            The AI response text (Markdown supported).
        metadata : str
            Optional metadata string like "2.1s · online".
        """
        # Extract metadata if embedded
        meta_match = re.search(r"<!--META:(.+?)-->", text)
        if meta_match:
            metadata = meta_match.group(1)
            text = re.sub(r"\n?<!--META:.+?-->", "", text).rstrip()

        # Convert markdown to HTML
        rendered = _md_to_html(text)

        # Build metadata line
        meta_html = ""
        if metadata:
            parts = metadata.split("|")
            elapsed = parts[0] if parts else ""
            mode = parts[1] if len(parts) > 1 else ""
            mode_icon = "🟢" if mode == "online" else "🟠"
            meta_html = (
                f'<div style="color:#64748b; font-size:11px; margin-top:6px;">'
                f'{mode_icon} {mode} · {elapsed}</div>'
            )

        bubble = (
            '<div style="text-align:left; margin:16px 0; padding:0 20px;">'
            '<div style="color:#8b5cf6; font-size:12px; margin-bottom:4px; '
            'font-weight:bold; letter-spacing:0.5px;">⚡ PHASE-5</div>'
            '<div style="color:#e2e8f0; display:inline-block; '
            'max-width:85%; text-align:left; font-size:14px; '
            f'line-height:1.7;">{rendered}</div>'
            f'{meta_html}'
            '</div>'
        )
        self.chat_display.append(bubble)
        self._scroll_to_bottom()

    def append_system(self, text: str) -> None:
        """Add a system/info message (centered, muted)."""
        bubble = (
            '<div style="text-align:center; margin:10px 0;">'
            f'<span style="color:#64748b; font-size:12px;">{text}</span></div>'
        )
        self.chat_display.append(bubble)
        self._scroll_to_bottom()

    # ------------------------------------------------------------------
    # Loading state
    # ------------------------------------------------------------------

    def set_loading(self, loading: bool) -> None:
        """Toggle the *thinking* state — disables input while AI works."""
        self.send_btn.setEnabled(not loading)
        self.input_field.setEnabled(not loading)
        if loading:
            self.input_field.setPlaceholderText("Phase-5 is thinking…")
            self.typing_indicator.start()
        else:
            self.input_field.setPlaceholderText("Ask anything")
            self.input_field.setFocus()
            self.typing_indicator.stop()

    def _on_attach(self) -> None:
        """Handle the + attach button — triggers screen capture / file attach."""
        self.append_system("📎 Tip: Use voice or type your request. Screen vision available via 'analyze my screen'.")



    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _on_send(self) -> None:
        text = self.input_field.text().strip()
        if not text:
            return
        self.input_field.clear()
        self.append_user(text)
        # Defer AI processing by one event-loop tick so the bubble renders instantly
        QTimer.singleShot(0, lambda: self.user_message.emit(text))

    def _on_toggle_tts(self) -> None:
        """Toggle text-to-speech output."""
        self.tts_enabled = not self.tts_enabled
        if self.tts_enabled:
            self.tts_btn.setText("🔊")
            self.tts_btn.setToolTip("Toggle voice response (ON)")
            self.append_system("🔊 Voice response enabled")
        else:
            self.tts_btn.setText("🔇")
            self.tts_btn.setToolTip("Toggle voice response (OFF)")
            self.append_system("🔇 Voice response disabled")

    def is_tts_enabled(self) -> bool:
        """Check if TTS is currently enabled."""
        return self.tts_enabled

    def _on_mic(self) -> None:
        """Toggle voice recording — first click starts, second click cancels."""
        if self._is_listening:
            # Second click → cancel the recording
            self._is_listening = False
            if self._voice_worker and self._voice_worker.isRunning():
                self._voice_worker.terminate()
                self._voice_worker.wait(500)
            self._reset_mic_style()
            self.append_system("🎙️ Voice input cancelled.")
            return

        self._is_listening = True
        # Red pulsing style while listening
        self.mic_btn.setStyleSheet(
            "QPushButton{background:#dc2626;color:#fff;border:none;"
            "border-radius:19px;font-size:15px;}"
            "QPushButton:hover{background:#b91c1c;}"
        )
        self.mic_btn.setToolTip("Click again to cancel")
        self.append_system("🎙️ Calibrating mic... speak in 0.3s!")

        worker = VoiceWorkerThread()
        self._voice_worker = worker
        worker.text_ready.connect(self._on_voice_result)
        worker.error.connect(self._on_voice_error)
        worker.finished.connect(self._reset_mic_style)
        worker.start()

    def _on_voice_result(self, text: str) -> None:
        """Handle successful voice transcription."""
        self._reset_mic_style()
        self.append_system(f'🎙️ You said: "{text}"')
        self.append_user(text)
        self.user_message.emit(text)

    def _on_voice_error(self, error: str) -> None:
        """Handle voice recognition failure."""
        self._reset_mic_style()
        self.append_system(f"⚠️ Voice: {error}")

    def _reset_mic_style(self) -> None:
        """Reset mic button to default pill style."""
        self._is_listening = False
        self.mic_btn.setStyleSheet(
            "QPushButton{background:transparent;color:#bbb;border:none;"
            "border-radius:19px;font-size:15px;}"
            "QPushButton:hover{background:#3a3a3a;}"
        )
        self.mic_btn.setToolTip("Voice input (Ctrl+M)")

    def _clear_chat(self) -> None:
        """Clear the chat display (Ctrl+L)."""
        self.chat_display.clear()
        self.append_system("⚡ Chat cleared. Start a new conversation!")

    def _scroll_to_bottom(self) -> None:
        sb = self.chat_display.verticalScrollBar()
        sb.setValue(sb.maximum())
