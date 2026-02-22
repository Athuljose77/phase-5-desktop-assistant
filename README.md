<div align="center">

# ⚡ Phase-5

### A Privacy-First Hybrid AI Desktop Assistant

*Cloud intelligence when online. Local AI when offline. Always private.*

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776ab?logo=python&logoColor=white)](https://python.org)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-41cd52?logo=qt&logoColor=white)](https://pypi.org/project/PyQt6/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 🧠 What is Phase-5?

Phase-5 is an **intelligent desktop assistant** that seamlessly switches between a powerful cloud LLM and a local offline model based on your internet connectivity. Unlike Siri, Cortana, or ChatGPT — Phase-5 **works without internet**, keeps your data **on your machine**, and gives you **full control over your OS** through natural language.

> **"Set my brightness to 50"** → ☀️ Done.  
> **"Open Chrome and play a video"** → ✅ Launched.  
> **"What are my system specs?"** → 💻 Full hardware report.  
> **"Shut down in 30 seconds"** → 🔴 Countdown started.

---

## ✨ Key Features

| Category | Capabilities |
|----------|-------------|
| 🤖 **Hybrid AI Engine** | Groq (Llama 3.3 70B) online → Ollama (Qwen 2.5) offline, with automatic fallback |
| 🖥️ **System Control** | Volume, brightness, screenshot, lock screen, shutdown/restart/sleep |
| 📁 **File Management** | Search, open, copy, move, rename, delete — all via natural language |
| 📱 **App Control** | Launch and close any installed application by name |
| 🌐 **Web & Network** | Open URLs in any browser, toggle WiFi on/off |
| 🧠 **Persistent Memory** | Remembers your name, preferences, and conversation history across sessions |
| 🔒 **Privacy-First** | Zero data sent to cloud in offline mode — everything stays local |
| 💬 **Natural Language** | Understands typos, casual phrasing, and even misspellings |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────┐
│                    Phase-5 App                    │
├──────────┬───────────────┬───────────┬───────────┤
│  PyQt6   │  Command      │  Hybrid   │  Memory   │
│  GUI     │  Handler      │  AI Engine│  Handler  │
│          │  (NLP Parse)  │           │  (JSON)   │
├──────────┴──────┬────────┴───┬───────┴───────────┤
│                 │            │                    │
│   System        │   ┌───────▼────────┐           │
│   Control       │   │  Internet? ✓/✗ │           │
│   (Win32 API)   │   └──┬─────────┬───┘           │
│                 │      │         │                │
│  • Volume       │   ┌──▼──┐  ┌──▼──┐             │
│  • Brightness   │   │ Groq│  │Ollam│             │
│  • Apps         │   │ API │  │a    │             │
│  • Files        │   │(70B)│  │(1.5B│             │
│  • Power        │   └─────┘  └─────┘             │
│  • WiFi         │   Online    Offline             │
└─────────────────┴────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+**
- **Ollama** installed and running ([ollama.com](https://ollama.com))
- *Optional*: Groq API key for online mode ([console.groq.com](https://console.groq.com))

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-username/phase-5.git
cd phase-5

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate    # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Pull the offline model
ollama pull qwen2.5:1.5b

# 5. Configure (optional — for online mode)
copy .env.example .env
# Edit .env and add your Groq API key

# 6. Run
python main.py
```

---

## ⚙️ Configuration

Create a `.env` file in the project root:

```env
# Online AI (Groq) — leave blank to use offline only
ONLINE_API_KEY=your-groq-api-key-here
ONLINE_MODEL=llama-3.3-70b-versatile
ONLINE_BASE_URL=https://api.groq.com/openai/v1/chat/completions

# Offline AI (Ollama)
OFFLINE_MODEL=qwen2.5:1.5b
OLLAMA_URL=http://localhost:11434/api/generate
```

---

## 🎮 Commands

Phase-5 understands natural language. Here are some examples:

```
"open notepad"                    → Launches Notepad
"close chrome"                    → Terminates Chrome
"set volume to 75"                → Sets audio to 75%
"dim the screen"                  → Reduces brightness
"take a screenshot"               → Saves to screenshots/
"lock my computer"                → Locks the workstation
"what are my system specs?"       → Shows CPU, RAM, OS info
"list files in Documents"         → Lists directory contents
"copy report.txt to Desktop"      → Copies file
"open youtube.com in chrome"      → Opens URL in Chrome
"shut down in 30 seconds"         → Initiates shutdown
"turn off wifi"                   → Disables WiFi adapter
```

---

## 🆚 How Phase-5 Compares

| Feature | Phase-5 | Siri | Cortana | ChatGPT |
|---------|---------|------|---------|---------|
| Works offline | ✅ | ❌ | ❌ | ❌ |
| Privacy-first (no cloud) | ✅ | ❌ | ❌ | ❌ |
| System control | ✅ | ⚠️ Limited | ⚠️ Limited | ❌ |
| File management | ✅ | ❌ | ❌ | ❌ |
| Open source | ✅ | ❌ | ❌ | ❌ |
| Hybrid AI (auto-switch) | ✅ | ❌ | ❌ | ❌ |
| Persistent memory | ✅ | ❌ | ❌ | ✅ |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| GUI Framework | PyQt6 |
| Online AI | Groq API (Llama 3.3 70B) |
| Offline AI | Ollama (Qwen 2.5 1.5B) |
| System Control | Win32 API, pycaw, psutil, pyautogui |
| Networking | requests, socket |

---

## 🗺️ Roadmap

- [x] Hybrid AI engine with auto-failover
- [x] System control (volume, brightness, power)
- [x] File management (CRUD, search)
- [x] App launch/close
- [x] Persistent memory across sessions
- [x] Dark-themed ChatGPT-style GUI
- [ ] Voice input (Whisper / speech_recognition)
- [ ] Voice output (TTS)
- [ ] Automation workflows & scheduled tasks
- [ ] Screen-aware context (OCR)
- [ ] Cross-platform support (macOS, Linux)
- [ ] Plugin system for extensions

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with ❤️ for the future of private AI assistants**

</div>
