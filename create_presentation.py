import os
from fpdf import FPDF

class PresentationPDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font('helvetica', 'B', 14)
            self.set_text_color(50, 50, 50)
            self.cell(0, 10, 'Phase-5 : Technical Presentation', align='R')
            self.ln(15)

    def footer(self):
        if self.page_no() > 1:
            self.set_y(-15)
            self.set_font('helvetica', 'I', 10)
            self.set_text_color(128, 128, 128)
            self.cell(0, 10, f'Slide {self.page_no()}', align='C')

    def slide_title(self, title):
        self.set_font('helvetica', 'B', 24)
        self.set_text_color(0, 51, 102)
        self.cell(0, 15, title, new_x="LMARGIN", new_y="NEXT", align='C')
        self.ln(10)

    def bullet(self, text):
        self.set_font('helvetica', '', 16)
        self.set_text_color(20, 20, 20)
        self.cell(10, 10, "-", new_x="RIGHT")
        self.multi_cell(0, 10, text)
        self.ln(5)

    def sub_bullet(self, text):
        self.set_font('helvetica', 'I', 14)
        self.set_text_color(60, 60, 60)
        self.cell(20, 8, "    *", new_x="RIGHT")
        self.multi_cell(0, 8, text)
        self.ln(3)

def create_presentation():
    # 'L' for Landscape, ideal for presenting
    pdf = PresentationPDF(orientation='L', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # -----------------------------
    # SLIDE 1: TITLE
    # -----------------------------
    pdf.add_page()
    pdf.set_y(70)
    pdf.set_font('helvetica', 'B', 48)
    pdf.set_text_color(41, 128, 185)
    pdf.cell(0, 25, 'PHASE-5', align='C', new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font('helvetica', '', 20)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 15, 'A Modular, Privacy-First Hybrid AI Desktop Assistant', align='C', new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(15)
    pdf.set_font('helvetica', 'I', 14)
    pdf.cell(0, 10, 'Technical Architecture & Implementation Review', align='C')
    
    # -----------------------------
    # SLIDE 2: CORE PROBLEM & SOLUTION
    # -----------------------------
    pdf.add_page()
    pdf.slide_title("The Problem & Phase-5 Solution")
    
    pdf.bullet("The Problem:")
    pdf.sub_bullet("Modern AI assistants (ChatGPT, Claude) are trapped in browsers.")
    pdf.sub_bullet("Native OS assistants (Siri, Cortana) lack advanced reasoning and are slow.")
    pdf.sub_bullet("Complete reliance on the cloud kills privacy and breaks during outages.")
    
    pdf.ln(5)
    pdf.bullet("The Solution: Phase-5")
    pdf.sub_bullet("A deeply integrated Windows desktop agent built in Python.")
    pdf.sub_bullet("Understands natural language and directly manipulates the OS.")
    pdf.sub_bullet("Uses a Dual-Engine approach: Cloud API for speed, Local LLM for offline resilience.")

    # -----------------------------
    # SLIDE 3: HYBRID AI ENGINE
    # -----------------------------
    pdf.add_page()
    pdf.slide_title("Dynamic Hybrid AI Engine")
    
    pdf.bullet("Online Mode (Cloud-API):")
    pdf.sub_bullet("Model: Groq Llama-3.1-8b / Llama-3.3-70b-versatile.")
    pdf.sub_bullet("Benefit: Ultra-fast LPUs (800+ Tokens/sec), high context handling.")
    pdf.sub_bullet("Trigger: Authorized .env API key + active socket connection.")
    
    pdf.ln(5)
    pdf.bullet("Offline Mode (Local Fallback):")
    pdf.sub_bullet("Model: Ollama Qwen 2.5 1.5B (Local Daemon).")
    pdf.sub_bullet("Benefit: Zero-latency, 100% data privacy, unaffected by internet outages.")
    pdf.sub_bullet("Trigger: Seamless automated fallback during a packet drop or ping failure.")

    # -----------------------------
    # SLIDE 4: OS AUTOMATION STACK
    # -----------------------------
    pdf.add_page()
    pdf.slide_title("Deep OS Automation & Interactivity")
    
    pdf.bullet("Win32 API & Hardware Manipulation (ctypes, pycaw, psutil)")
    pdf.sub_bullet("Adjust volume levels, manage displays (WMI), mute endpoints.")
    pdf.sub_bullet("Gracefully sleep, terminate processes, lock workstation, or shut down.")
    
    pdf.bullet("Filesystem CRUD Sandbox (os, shutil)")
    pdf.sub_bullet("Natural language parsing triggers localized Python file actions.")
    pdf.sub_bullet("Copy, move, rename, delete, and list directory contents securely.")
    
    pdf.bullet("Application Lifecycle Control")
    pdf.sub_bullet("Extracts paths from Windows Registry & Start Menu shortcuts to launch generic apps.")

    # -----------------------------
    # SLIDE 5: NLP COMMAND PARSING
    # -----------------------------
    pdf.add_page()
    pdf.slide_title("Regex NLP Parsing Engine")
    
    pdf.set_font('helvetica', '', 14)
    pdf.multi_cell(0, 8, "To avoid expensive, slow LLM processing for basic system tasks, Phase-5 uses a pre-flight NLP parser.")
    pdf.ln(5)
    
    pdf.bullet("Fuzzy String Matching")
    pdf.sub_bullet("Absorbs typos natively ('shtudown', 'pn notepad').")
    
    pdf.bullet("Extractive Regex Expressions")
    pdf.sub_bullet("Splits 'send an email to boss subject Update body Done' into modular payloads.")
    pdf.sub_bullet("Instantly routes matched intents to specific Python subsystem classes.")
    
    pdf.bullet("AI Fallback")
    pdf.sub_bullet("If the Regex Engine finds no hardcoded system match, the query is passed to the LLM for chat/reasoning.")

    # -----------------------------
    # SLIDE 6: UI & COMMUNICATIONS PROTOCOL
    # -----------------------------
    pdf.add_page()
    pdf.slide_title("Communications & User Interface")
    
    pdf.bullet("PyQt6 Asynchronous Interface")
    pdf.sub_bullet("Terminal-inspired 'Matrix' style GUI with strict QThread separation.")
    pdf.sub_bullet("Prevents UI freezing during heavy AI token streaming or sub-process wait blocks.")
    
    pdf.ln(5)
    pdf.bullet("WhatsApp & Multi-Browser Gmail Automations")
    pdf.sub_bullet("Phase-5 manages external GUIs through PyAutoGUI visual math and Keyboard Events.")
    pdf.sub_bullet("Executes URL parametric routing (e.g. mail.google.com/mail/?view=cm&to=X).")
    pdf.sub_bullet("Handles automated window focusing (SetForegroundWindow) to inject 'Ctrl+Enter' sends.")

    # -----------------------------
    # SLIDE 7: ROADMAP
    # -----------------------------
    pdf.add_page()
    pdf.slide_title("Future Upgrades & Roadmap")
    
    pdf.bullet("1. Computer Vision Integration")
    pdf.sub_bullet("Allowing the model to take screenshots and perform OCR to 'see' the user's screen.")
    
    pdf.bullet("2. Local Voice Recognition")
    pdf.sub_bullet("Implementing OpenAI Whisper on CPU/GPU for hands-free dictated commands.")
    
    pdf.bullet("3. Task Scheduling Daemon")
    pdf.sub_bullet("Persistent chron-job processing (e.g., 'every day at 5 PM close Slack and Sleep').")
    
    pdf.bullet("4. Headless Browser Web Scraping")
    pdf.sub_bullet("Integrating Playwright to crawl the internet fully autonomously for research.")


    # OUTPUT
    out_path = os.path.join(os.getcwd(), 'Phase-5_Technical_Presentation.pdf')
    pdf.output(out_path)
    print("Presentation successfully generated at:", out_path)

if __name__ == '__main__':
    create_presentation()
