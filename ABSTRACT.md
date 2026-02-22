# Phase-5: A Privacy-First Hybrid AI Desktop Assistant

## Abstract

Phase-5 is an intelligent desktop assistant that operates in a hybrid online-offline architecture, automatically switching between a cloud LLM (Groq API) and a local offline model (Ollama) based on internet availability. Unlike conventional AI assistants that are fully cloud-dependent, Phase-5 ensures uninterrupted assistance regardless of network conditions while keeping user data private. Beyond conversation, it offers deep system-level control — users can launch/close applications, adjust volume and brightness, manage files, take screenshots, and retrieve system diagnostics, all through natural language. The assistant features persistent memory across sessions and a modern PyQt6 chat interface with real-time mode indication.

## Current Stage

Phase-5 is currently a **working prototype**. The hybrid AI engine is fully functional with seamless online/offline switching and automatic fallback. Users can control system settings (volume, brightness, lock, shutdown, sleep), launch and close applications, manage files (search, copy, move, rename, delete), take screenshots, retrieve system specs, toggle WiFi, and open websites — all through natural language commands. The assistant remembers user context across sessions via persistent JSON-based memory. A dark-themed PyQt6 chat interface with real-time online/offline status indication serves as the front end.

## Idea Stage

**Problem:** Existing AI assistants are entirely cloud-dependent, raising privacy concerns, failing without internet, and offering limited OS-level control.

**Solution:** A hybrid AI assistant that provides cloud-quality intelligence when online, reliable local AI when offline, and direct natural language control over the user's desktop — all with a privacy-first approach where no data leaves the machine in offline mode.

**Tech Stack:** Python, PyQt6, Groq API (Llama 3.3 70B), Ollama (Qwen 2.5), Win32 API, psutil

**Future Scope:** Voice interaction (Whisper + TTS), automation workflows, screen-aware context, cross-platform support, plugin system.
