import os
import sys
import subprocess

try:
    from fpdf import FPDF
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fpdf2", "-q"])
    from fpdf import FPDF

class ArchPDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font('helvetica', 'B', 10)
            self.set_text_color(120, 120, 120)
            self.cell(0, 10, 'Phase-5 : Software Architecture Specification', align='R')
            self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

    def h1(self, title):
        self.set_font('helvetica', 'B', 20)
        self.set_text_color(0, 51, 102)
        self.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def h2(self, title):
        self.set_font('helvetica', 'B', 14)
        self.set_text_color(40, 70, 120)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def h3(self, title):
        self.set_font('helvetica', 'B', 12)
        self.set_text_color(60, 60, 60)
        self.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def p(self, text):
        self.set_font('helvetica', '', 11)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 6, text)
        self.ln(4)

    def code_box(self, text):
        self.set_font('courier', '', 10)
        self.set_fill_color(245, 245, 245)
        self.multi_cell(0, 6, text, fill=True)
        self.ln(4)

def generate_architecture_doc():
    pdf = ArchPDF(orientation="P", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # --- TITLE PAGE ---
    pdf.set_y(50)
    pdf.set_font('helvetica', 'B', 36)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 20, 'PHASE-5', align='C', new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font('helvetica', 'B', 18)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 10, 'Software Architecture & Data Flow Specification', align='C', new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(30)
    pdf.set_font('helvetica', '', 12)
    pdf.multi_cell(0, 6, 
        "This document outlines the complete architectural topology of the Phase-5 Desktop Assistant. "
        "It details the module hierarchy, the Natural Language Processing (NLP) routing logic, the "
        "hybrid AI context handlers, and the integration paradigms used to control the host Operating System.",
        align='C'
    )
    
    # --- SECTION 1 ---
    pdf.add_page()
    pdf.h1("1. High-Level Architectural Topology")
    pdf.p(
        "Phase-5 is structured as a monolithic Python application utilizing the Model-View-Controller (MVC) "
        "pattern. The architecture isolates the User Interface from the complex AI context handlers and the "
        "dangerous System Control APIs."
    )
    
    pdf.code_box(
        "+-------------------------------------------------------+\n"
        "|                 USER (Keyboard/Voice)                 |\n"
        "+--------------------------+----------------------------+\n"
        "                           | (Input event)\n"
        "                           v\n"
        "+--------------------------+----------------------------+\n"
        "|   FRONTEND (gui.py via PyQt6 QThread Event Loop)      |\n"
        "+--------------------------+----------------------------+\n"
        "                           | (Main App Dispatcher)\n"
        "                           v\n"
        "+----------------+-------------------+------------------+\n"
        "|   NLP PARSER   |      HYBRID       |   SYSTEM LEVEL   |\n"
        "| (command_      |      AI ENGINE    |   CONTROLLER     |\n"
        "|  handler.py)   |   (ai_handler.py) |(system_control.py|\n"
        "+-------+--------+---------+---------+---------+--------+\n"
        "        |                  |                   |\n"
        "        | Match?           | Fallback          | Win32\n"
        "        v                  v                   v\n"
        " [Exact Functions]  [Groq <-> Ollama]   [Hardware / Files]"
    )
    
    pdf.p(
        "By enforcing strict separation of concerns, the Graphical User Interface (`gui.py`) never directly "
        "makes HTTP requests or invokes Win32 API commands. Instead, it dispatches user intents down to the "
        "Core Handlers and waits for an asynchronous response."
    )

    # --- SECTION 2 ---
    pdf.h1("2. Core Modules & execution Flow")
    
    pdf.h2("2.1. The Entry Point (main.py)")
    pdf.p(
        "The `main.py` file bootstraps the environment. It checks for `.env` configurations, validates internet "
        "connectivity using `connectivity.py`, drops the environment variables into the context, and launches the "
        "PyQt6 `QApplication`. It instantiates all Core module singletons (MemoryHandler, HybridAIHandler, CommandHandler)."
    )
    
    pdf.h2("2.2. The GUI Subsystem (gui.py)")
    pdf.p(
        "The `MainWindow` class inherits from `QMainWindow`. Because PyQt6 is strictly single-threaded for UI actions, "
        "Phase-5 uses QThread subclassing (`WorkerThread`). When a user types a command, a `WorkerThread` is spun up in "
        "the background to process the LLM request or heavy OS operation, emitting `pyqtSignals` back to the main thread "
        "to rapidly append text characters to the UI (creating the smooth 'typing' effect)."
    )

    # --- SECTION 3 ---
    pdf.add_page()
    pdf.h1("3. The Intelligence Routing Paradigm")
    
    pdf.h2("3.1. Level-1: The NLP Command Parser (command_handler.py)")
    pdf.p(
        "To preserve API tokens, reduce latency, and prevent LLM hallucinations from accidentally deleting files, "
        "Phase-5 uses a preemptive parsing layer. Before any text touches an AI model, it passes through `CommandHandler.parse()`."
    )
    pdf.h3("The Parsing Pipeline:")
    pdf.p(
        "1. Input is stripped of whitespace and forced to lowercase.\n"
        "2. A Fuzzy Matcher corrects obvious typos ('shutdwon' intercepts 'shutdown').\n"
        "3. A cascade of Regular Expressions evaluates the intent.\n"
        "4. If a match occurs (e.g., regex `r\"(?:open|launch)\\s+(.+)\"` triggers on 'open notepad'), the parser returns "
        "a strict tuple: `('execute_open', 'notepad')`.\n"
        "5. The main dispatcher intercepts this tuple and instantly fires the System Control module, completely bypassing the AI."
    )
    
    pdf.h2("3.2. Level-2: The Hybrid AI Engine (hybrid_handler.py)")
    pdf.p(
        "If `command_handler.py` detects an unknown intent (a generic question or conversation), it forwards the string to "
        "the Hybrid AI Engine. This engine is resilient and ping-aware."
    )
    pdf.h3("A. The Online Handler (Groq API)")
    pdf.p(
        "Utilizes the standard OpenAI client schema but points to `api.groq.com`. It streams tokens from models like "
        "`llama-3.1-8b-instant`. This is the preferred state due to immense speed and sophisticated reasoning."
    )
    pdf.h3("B. The Offline Handler (Ollama HTTP Socket)")
    pdf.p(
        "If the network request to Groq times out, or if `connectivity.py` flags a dropped socket, the request silently "
        "fails over to `offline_handler.py`. It constructs a JSON payload containing the prompt and `context[]` arrays "
        "and posts it to `http://localhost:11434/api/generate`, streaming tokens from the local `Qwen 2.5` daemon."
    )

    # --- SECTION 4 ---
    pdf.add_page()
    pdf.h1("4. The Operating System Integrations")
    pdf.p(
        "The `system_control.py` module is a static class repository containing over 30 distinct OS-manipulation "
        "functions. It acts as the bridge between Python and pure Windows C routines."
    )
    
    pdf.h2("4.1. Hardware Manipulation Stack")
    pdf.p(
        "- Windows ctypes: Used for `windll.user32.LockWorkStation()` and power management flags.\n"
        "- Pycaw & COM Interfaces: To bind to the `IAudioEndpointVolume` controller, allowing programmatic mathematical "
        "calculations (e.g., 'Volume = 50%') to be translated into pure decibel scaling scalars.\n"
        "- WMI (Windows Management Instrumentation): Utilized to map string commands to underlying monitor brightness scopes."
    )
    
    pdf.h2("4.2. GUI Navigation & Protocol Actions")
    pdf.p(
        "Phase-5 possesses Agentic capabilities to navigate third-party software when APIs are unavailable."
    )
    pdf.h3("WhatsApp Automation Logic:")
    pdf.p(
        "When ordered to send a message, Phase-5 calculates relative Screen DPI arrays. It locates the `whatsapp://` URI, "
        "identifies the active window handle (`HWND`) via `win32gui`, mathematically asserts the search bar coordinates, "
        "and injects keystrokes via `pyautogui` to silently dispatch human-like messaging."
    )
    pdf.h3("Email Protocol Injection:")
    pdf.p(
        "The system scans `Program Files` for Edge, Chrome, and Brave executables. By formatting a specialized HTTPS string "
        "(`mail.google.com/mail/?view=cm&to={x}&su={y}`), it loads the compose draft in a designated graphical window. A `SetForegroundWindow` "
        "hook secures keyboard focus, followed by a simulated `Ctrl+Enter` dispatch."
    )

    # --- SECTION 5 ---
    pdf.add_page()
    pdf.h1("5. Persistent Memory Paradigm")
    pdf.p(
        "The `memory_handler.py` retains context by reading/writing a `memory.json` file on the hard disk. "
        "This file holds multiple arrays:"
    )
    pdf.p(
        "- History Matrix: A sliding window of the last 20 messages. Older messages are constantly popped from the array "
        "to prevent exceeding the LLM's Maximum Token Context window.\n"
        "- Identity Storage: Safely extracts names (e.g., 'My name is John') and pins them to a persistent metadata block, "
        "which is subsequently injected into the immutable System Prompt of the LLM upon every initialization."
    )
    
    pdf.ln(10)
    pdf.h1("6. Documentation Scope Closure")
    pdf.p(
        "The Phase-5 architecture provides distinct isolation boundaries between reasoning (AI), parsing (NLP), and "
        "execution (System). By maintaining this separation, the project allows modular replacement of the AI engines, "
        "scalability across host operating systems, and absolute stability via offline continuity checks."
    )

    out_path = os.path.join(os.getcwd(), 'Phase-5_Full_Architecture_Spec.pdf')
    pdf.output(out_path)
    print("Architectural PDF successfully generated at:", out_path)

if __name__ == '__main__':
    generate_architecture_doc()
