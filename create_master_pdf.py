import os
import sys
import subprocess

try:
    from fpdf import FPDF
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fpdf2", "-q"])
    from fpdf import FPDF

class MasterPDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font('helvetica', 'B', 10)
            self.set_text_color(100, 100, 100)
            self.cell(0, 10, 'Phase-5 : Complete Architecture & Technical Details', align='R')
            self.ln(12)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

    def h1(self, title):
        self.set_font('helvetica', 'B', 20)
        self.set_text_color(20, 40, 80)
        self.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def h2(self, title):
        self.set_font('helvetica', 'B', 14)
        self.set_text_color(40, 80, 140)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def h3(self, title):
        self.set_font('helvetica', 'B', 12)
        self.set_text_color(80, 80, 80)
        self.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def p(self, text):
        self.set_font('helvetica', '', 11)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 6, text)
        self.ln(4)

    def bullet(self, title, text=""):
        self.set_font('helvetica', 'B', 11)
        self.cell(5, 6, "-", new_x="RIGHT")
        if text:
            self.cell(45, 6, title + ": ", new_x="RIGHT")
            self.set_font('helvetica', '', 11)
            self.multi_cell(0, 6, text)
        else:
            self.set_font('helvetica', '', 11)
            self.multi_cell(0, 6, title)
        self.ln(2)

    def code_box(self, text):
        self.set_font('courier', '', 10)
        self.set_fill_color(245, 245, 245)
        self.multi_cell(0, 6, text, fill=True)
        self.ln(4)

def generate_master_pdf():
    pdf = MasterPDF(orientation="P", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # -----------------------------
    # TITLE PAGE
    # -----------------------------
    pdf.add_page()
    pdf.set_y(60)
    pdf.set_font('helvetica', 'B', 38)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 20, 'PHASE-5', align='C', new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font('helvetica', 'B', 16)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 10, 'A Privacy-First Hybrid AI Desktop Assistant', align='C', new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(25)
    pdf.set_font('helvetica', '', 14)
    pdf.cell(0, 8, 'Complete Architecture & Technical Details', align='C', new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(10)
    pdf.set_font('helvetica', 'I', 11)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 6, 
        "This master document serves as the comprehensive guide to Phase-5. "
        "It aggressively details both the broad user-facing functional capabilities and the underlying "
        "structural architecture, data flow, NLP routing logic, and Operating System integrations.",
        align='C'
    )
    
    # -----------------------------
    # SECTION 1: EXECUTIVE SUMMARY
    # -----------------------------
    pdf.add_page()
    pdf.h1("1. Executive Summary")
    pdf.p(
        "Phase-5 represents a paradigm shift in local computing interfaces. Traditional AI assistants (ChatGPT, Claude) "
        "live inside a web browser sandbox. Native operating system assistants (Cortana, Siri) lack profound logical "
        "reasoning capabilities. Phase-5 bridges this massive gap.\n\n"
        "It acts as a deeply integrated local software agent, capable of extreme system manipulation-from adjusting "
        "hardware brightness to fully automating browser sessions for email drafts, all powered by a brilliant hybrid "
        "LLM brain. More importantly, it features an 'air-gapped' fallback system that retains functionality even without internet access."
    )
    
    # -----------------------------
    # SECTION 2: HIGH-LEVEL TOPOLOGY
    # -----------------------------
    pdf.h1("2. High-Level Architecture Topology")
    pdf.p("Phase-5 isolates the GUI from the dangerous OS API hooks and from the token-heavy LLMs.")
    
    pdf.code_box(
        "+-------------------------------------------------------+\n"
        "|                 USER (PyQt6 Interface)                |\n"
        "+--------------------------+----------------------------+\n"
        "                           | (Async Task Queueing)\n"
        "                           v\n"
        "+--------------------------+----------------------------+\n"
        "|        NLP PIPELINE (command_handler.py)              |\n"
        "|   [Fuzzy Matcher -> Extractive Regex -> Classifier]   |\n"
        "+--------------------------+----------------------------+\n"
        "                           | \n"
        "        +------------------+-----------------+\n"
        "   (Raw OS Intent)                    (Generic Chat Intent)\n"
        "        v                                    v\n"
        "+------------------+                +-------------------+\n"
        "| SYSTEM CONTROL   |                | HYBRID AI ENGINE  |\n"
        "| (Windows API)    |                | (Groq / Ollama)   |\n"
        "+------------------+                +-------------------+"
    )
    
    pdf.p(
        "By enforcing strict separation of concerns, the Graphical User Interface (gui.py) never blocks waiting "
        "for an HTTP request or a sluggish file read. It dispatches intents down to the Core Handlers via background "
        "QThreads."
    )

    # -----------------------------
    # SECTION 3: HYBRID AI ENGINE
    # -----------------------------
    pdf.add_page()
    pdf.h1("3. The Hybrid AI Engine")
    pdf.p(
        "The standout mechanism of Phase-5 is its zero-downtime intelligence routing. The `hybrid_handler.py` acts "
        "as a dynamic proxy server for LLM inference."
    )
    
    pdf.h2("3.1. Online Mode (Groq Llama 3.3)")
    pdf.p(
        "When `connectivity.py` confirms a live internet socket, Phase-5 binds to the Groq API infrastructure. "
        "Utilizing their ultra-fast LPU inference engine, it accesses models like Llama-3.1-8b and Llama-3.3-70b-versatile. "
        "This offers superlative reasoning, high context awareness, and generation speeds that exceed 800 tokens per second."
    )
    
    pdf.h2("3.2. Offline Mode (Local Ollama Qwen)")
    pdf.p(
        "Upon detecting a packet drop or network timeout, the application degrades silently to 'Offline Mode'. "
        "In this air-gapped state, instructions pipe to a locally hosted Ollama daemon running the Qwen 2.5 1.5B model. "
        "Absolute data privacy is guaranteed, as zero tokens leave the chassis."
    )

    # -----------------------------
    # SECTION 4: NLP PARSING & ROUTING
    # -----------------------------
    pdf.h1("4. Advanced NLP Parsing Pipeline")
    pdf.p(
        "Passing basic system commands (e.g., 'open notepad') to a 70 Billion parameter LLM is wasteful and slow. "
        "Phase-5 implements a hyper-optimized Regular Expression engine combined with Levenshtein fuzzy string matching."
    )
    
    pdf.h3("The Pre-Flight Pipeline:")
    pdf.p(
        "1. Input is standardized (whitespace stripped, forced to lowercase).\n"
        "2. Fuzzy Matcher corrects typos in real-time ('opne' becomes 'open').\n"
        "3. Regex evaluates intent based on syntactic anchors.\n"
        "4. If exact intent is mapped, it executes deterministic Win32 functions instantly.\n"
        "5. If unmapped, the string is shipped to the Hybrid AI Engine."
    )

    pdf.code_box(
        "\"open youtube.com in chrome\"\n"
        "   -> Parsed Tuple: ('open_url', 'youtube.com|chrome')\n\n"
        "\"send an email to boss subject Status body Done\"\n"
        "   -> Parsed Tuple: ('email', 'boss|Status|Done')\n\n"
        "\"Why is the sky blue?\"\n"
        "   -> Parsed Tuple: ('chat', 'Why is the sky blue?')"
    )

    # -----------------------------
    # SECTION 5: SYSTEM STACK
    # -----------------------------
    pdf.add_page()
    pdf.h1("5. Deep Windows OS Integration")
    pdf.p(
        "The `system_control.py` module houses over 30 distinct hardware-level manipulations and file operation utilities, "
        "binding Python directly to the lowest levels of Windows."
    )
    
    pdf.h2("5.1. Hardware Manipulation")
    pdf.bullet("Audio Routing", "Utilizes `pycaw` and COM Interfaces to calculate and set absolute decibel scales on the system mixer.")
    pdf.bullet("Display Tuning", "Employs Windows Management Instrumentation (WMI) to forcefully alter monitor brightness percentages.")
    pdf.bullet("Power Interupts", "Hooks into `ctypes.windll.user32.LockWorkStation()` for instantaneous lock states, alongside psutil shutdown invokes.")
    
    pdf.h2("5.2. File System Management")
    pdf.bullet("Context Access", "The agent can natively read `.txt`, `.py`, `.md` or `.json` files straight into its AI memory queue (RAG context).")
    pdf.bullet("CRUD Sandbox", "Translates phrases like 'copy X to Desktop' into absolute pathing operations via `shutil`.")
    
    # -----------------------------
    # SECTION 6: COMMUNICATIONS AUTOMATION
    # -----------------------------
    pdf.h1("6. External Communications Algorithms")
    pdf.p(
        "Phase-5 automates standard third-party graphical interfaces to send messages."
    )
    
    pdf.h2("6.1. WhatsApp Desktop Protocol")
    pdf.p(
        "Triggering an autonomous WhatsApp command causes the system to launch the `whatsapp://` URI payload. "
        "Phase-5 then calculates display DPI arrays, selects the active WhatsApp `HWND`, mechanically asserts the Search Bar coordinates, "
        "types the contact structure using `pyautogui.typewrite()`, and auto-sends the payload hands-free."
    )
    
    pdf.h2("6.2. Multi-Browser Gmail Injector")
    pdf.p(
        "The agent parses To, Subject, and Body parameters. It detects local Chrome, Edge, and Brave executables. "
        "Upon firing, it structures a dense HTTP GET query straight to `mail.google.com/mail/?view=cm...` bypassing "
        "the standard dashboard. It waits 6 seconds for DOM render, aggressively forces the window into Focus (`SetForegroundWindow`), "
        "and triggers a physical 'Ctrl+Enter' equivalent to hit send without a mouse click."
    )

    # -----------------------------
    # SECTION 7: CORE LIBRARIES & TECH STACK
    # -----------------------------
    pdf.add_page()
    pdf.h1("7. Implementation Tech Stack")
    pdf.p("The Phase-5 repository uses heavily typed, modular Python 3.10+ files.")
    
    pdf.bullet("Language", "Python 3.10+ (Static Typing enabled)")
    pdf.bullet("Interface/GUI", "PyQt6 (QThread, PyQtSignals, Markdown rendering)")
    pdf.bullet("AI Adapters", "Groq Core SDK, PyOllama")
    pdf.bullet("Hardware Hooks", "ctypes, win32gui, win32con, win32api, psutil, pycaw, WMI")
    pdf.bullet("RPA / UI Automation", "pyautogui, subprocess, webbrowser")
    
    # -----------------------------
    # SECTION 8: ROADMAP
    # -----------------------------
    pdf.h1("8. Development Roadmap")
    pdf.p(
        "As a living agentic framework, the Phase-5 architecture is built to support immediate "
        "future expansions:"
    )
    pdf.bullet("Local Speech-To-Text", "Integration of OpenAI Whisper for entirely local voice inference.")
    pdf.bullet("Agentic Computer Vision", "Implementation of automated screen capture feeding into a multimodal LLM to allow the system to 'see' what the user is pointing at.")
    pdf.bullet("Headless Web Crawling", "Playwright integrations to allow Phase-5 to browse dynamic websites silently and summarize real-time web data.")
    
    pdf.ln(10)
    pdf.set_font('helvetica', 'I', 11)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 10, 'Phase-5 : Built to redefine native desktop autonomy.', align='C')

    # Output
    out_path = os.path.join(os.getcwd(), 'Phase-5_Master_Technical_Document.pdf')
    pdf.output(out_path)
    print("Master PDF successfully generated at:", out_path)

if __name__ == '__main__':
    generate_master_pdf()
