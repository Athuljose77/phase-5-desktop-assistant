"""
Phase-5 — First-Run Setup Wizard
Shown when .env is missing or ONLINE_API_KEY is not set.
Securely collects the Groq API key and saves it to .env.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt  # type: ignore[import-not-found]
from PyQt6.QtGui import QFont  # type: ignore[import-not-found]
from PyQt6.QtWidgets import (  # type: ignore[import-not-found]
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

_ENV_PATH = Path(__file__).parent / ".env"


def needs_setup() -> bool:
    """Return True if .env is missing or API key is placeholder/empty."""
    if not _ENV_PATH.exists():
        return True
    for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("ONLINE_API_KEY="):
            val = line.split("=", 1)[1].strip()
            return not val or val == "your-groq-api-key-here"
    return True


def _save_key(api_key: str) -> None:
    """Write (or update) ONLINE_API_KEY in .env without touching other lines."""
    if _ENV_PATH.exists():
        lines = _ENV_PATH.read_text(encoding="utf-8").splitlines()
        new_lines = []
        found = False
        for ln in lines:
            if ln.strip().startswith("ONLINE_API_KEY="):
                new_lines.append(f"ONLINE_API_KEY={api_key}")
                found = True
            else:
                new_lines.append(ln)
        if not found:
            new_lines.append(f"ONLINE_API_KEY={api_key}")
        _ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    else:
        # Create .env from the example template if it exists, else minimal
        example = Path(__file__).parent / ".env.example"
        if example.exists():
            content = example.read_text(encoding="utf-8")
            content = content.replace("your-groq-api-key-here", api_key)
        else:
            content = (
                f"ONLINE_API_KEY={api_key}\n"
                "ONLINE_MODEL=llama-3.1-8b-instant\n"
                "OFFLINE_MODEL=qwen2.5:1.5b\n"
            )
        _ENV_PATH.write_text(content, encoding="utf-8")


class SetupWizard(QDialog):
    """Modal dialog that collects the Groq API key on first run."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Phase-5 — First-Time Setup")
        self.setMinimumWidth(520)
        self.setModal(True)
        self.setStyleSheet("background-color: #1c1c1c; color: #e8e8e8;")
        self._accepted = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 32, 36, 28)
        layout.setSpacing(16)

        # Title
        title = QLabel("⚡ Welcome to Phase-5")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #e8e8e8; background: transparent;")
        layout.addWidget(title)

        # Sub-text
        sub = QLabel(
            "To use the online AI (Groq), enter your free API key below.\n"
            "It is saved locally only — never uploaded anywhere."
        )
        sub.setFont(QFont("Segoe UI", 11))
        sub.setStyleSheet("color: #999; background: transparent;")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        # Link
        link = QLabel(
            '→ Get a free key at <a href="https://console.groq.com" '
            'style="color:#8b5cf6;">console.groq.com</a>'
        )
        link.setFont(QFont("Segoe UI", 10))
        link.setStyleSheet("background: transparent;")
        link.setOpenExternalLinks(True)
        link.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(link)

        # Key input
        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText("gsk_...")
        self._key_input.setFont(QFont("Segoe UI", 12))
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)  # masks the key
        self._key_input.setStyleSheet(
            "background:#2b2b2b; color:#e8e8e8; border:1px solid #3a3a3a;"
            "border-radius:10px; padding:10px 14px;"
        )
        layout.addWidget(self._key_input)

        # Show/hide toggle
        self._show_btn = QPushButton("Show")
        self._show_btn.setFixedWidth(64)
        self._show_btn.setStyleSheet(
            "QPushButton{background:#3a3a3a;color:#bbb;border:none;"
            "border-radius:8px;padding:6px 10px;font-size:11px;}"
            "QPushButton:hover{background:#4a4a4a;}"
        )
        self._show_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._show_btn.clicked.connect(self._toggle_show)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self._show_btn)
        layout.addLayout(row)

        self._status = QLabel("")
        self._status.setFont(QFont("Segoe UI", 10))
        self._status.setStyleSheet("color:#f87171; background:transparent;")
        layout.addWidget(self._status)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        skip_btn = QPushButton("Skip (Offline only)")
        skip_btn.setStyleSheet(
            "QPushButton{background:#2b2b2b;color:#888;border:1px solid #3a3a3a;"
            "border-radius:10px;padding:10px 20px;font-size:12px;}"
            "QPushButton:hover{background:#3a3a3a;}"
        )
        skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        skip_btn.clicked.connect(self.reject)
        btn_row.addWidget(skip_btn)

        save_btn = QPushButton("Save & Continue →")
        save_btn.setStyleSheet(
            "QPushButton{background:#7c3aed;color:#fff;border:none;"
            "border-radius:10px;padding:10px 24px;font-size:13px;font-weight:bold;}"
            "QPushButton:hover{background:#8b5cf6;}"
        )
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

    def _toggle_show(self) -> None:
        if self._key_input.echoMode() == QLineEdit.EchoMode.Password:
            self._key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._show_btn.setText("Hide")
        else:
            self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._show_btn.setText("Show")

    def _on_save(self) -> None:
        key = self._key_input.text().strip()
        if not key:
            self._status.setText("⚠ Please enter an API key.")
            return
        if not key.startswith("gsk_"):
            self._status.setText("⚠ Groq keys should start with 'gsk_'. Check and try again.")
            return
        _save_key(key)
        self._accepted = True
        self.accept()

    def was_saved(self) -> bool:
        return self._accepted


def run_setup_if_needed() -> bool:
    """Show the setup wizard if needed. Returns True if app should continue."""
    if not needs_setup():
        return True

    from PyQt6.QtWidgets import QApplication  # type: ignore[import-not-found]
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    wizard = SetupWizard()
    wizard.exec()
    return True  # Always continue (skip = offline only mode)
