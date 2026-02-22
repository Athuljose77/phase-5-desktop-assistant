import subprocess
import sys
import os

try:
    from fpdf import FPDF
except ImportError:
    print("Installing fpdf2...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fpdf2", "-q"])
    from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        # We only want the header on pages after the title page
        if self.page_no() > 1:
            self.set_font('helvetica', 'B', 12)
            self.set_text_color(150, 150, 150)
            self.cell(0, 10, 'Phase-5 : Technical Documentation & Project Portfolio', align='R')
            self.ln(15)

    def footer(self):
        if self.page_no() > 1:
            self.set_y(-15)
            self.set_font('helvetica', 'I', 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 10, f'Page {self.page_no()}', align='C')

    def chapter_title(self, title):
        self.set_font('helvetica', 'B', 18)
        self.set_text_color(30, 60, 100)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def sub_title(self, title):
        self.set_font('helvetica', 'B', 14)
        self.set_text_color(50, 80, 120)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def chapter_body(self, body):
        self.set_font('helvetica', '', 11)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 6, body)
        self.ln(4)

    def bullet_point(self, title, text=""):
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

    def code_block(self, code):
        self.set_font('courier', '', 10)
        self.set_fill_color(240, 240, 240)
        self.multi_cell(0, 6, code, fill=True)
        self.ln(5)

def create_pdf():
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # -----------------------------
    # TITLE PAGE
    # -----------------------------
    pdf.add_page("P", format="A4")
    pdf.set_y(80)
    pdf.set_font('helvetica', 'B', 32)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 20, 'PHASE-5', align='C', new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font('helvetica', 'B', 16)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, 'A Privacy-First Hybrid AI Desktop Assistant', align='C', new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(20)
    pdf.set_font('helvetica', '', 12)
    pdf.cell(0, 8, 'Comprehensive Technical Documentation & Architecture', align='C', new_x="LMARGIN", new_y="NEXT")
    
    pdf.add_page()
    
    # -----------------------------
    # 1. EXECUTIVE SUMMARY
    # -----------------------------
    pdf.chapter_title('1. Executive Summary')
    intro = (
        "Phase-5 represents a paradigm shift in how users interact with their personal computers. "
        "Unlike standard Web-based AI chat interfaces (such as ChatGPT or Claude) that live in the browser, or "
        "cloud-locked operating system assistants (like Cortana or Siri), Phase-5 is built as a deeply integrated, "
        "privacy-first, local agent.\n\n"
        "Its primary objective is to 'bridge the gap' between massive natural language generation models and hard "
        "Win32 system programming. Phase-5 parses casual human text-and in the future, voice-translating it "
        "into executable Python behaviors that manipulate desktop environments, orchestrate filesystem rules, "
        "configure Windows hardware, and handle desktop applications directly."
    )
    pdf.chapter_body(intro)

    # -----------------------------
    # 2. HYBRID ARCHITECTURE
    # -----------------------------
    pdf.chapter_title('2. The Hybrid AI Architecture & Failover')
    engine_desc = (
        "The cornerstone of Phase-5's reliability is its resilient dual-engine architecture. It ensures that the user is "
        "never locked out of their AI interface due to internet outages or API server downtime."
    )
    pdf.chapter_body(engine_desc)
    
    pdf.sub_title('2.1. Online Mode (Groq Llama 3.3 70B)')
    groq_desc = (
        "When the network is active, Phase-5 binds to the Groq API infrastructure. Utilizing the ultra-fast LPU "
        "inference engine, it accesses models like Llama-3.1-8b and Llama-3.3-70b-versatile. This mode offers "
        "superlative conversational reasoning, coding generation, and complex logic resolution at speeds often "
        "exceeding 800 tokens per second."
    )
    pdf.chapter_body(groq_desc)
    
    pdf.sub_title('2.2. Offline Mode (Local Ollama Qwen 2.5)')
    ollama_desc = (
        "Phase-5 pings a remote server consistently. Upon detecting a packet drop or network timeout, the application "
        "gracefully downgrades to 'Offline Mode' without user intervention. In this state, it pipes instructions to a "
        "locally hosted Ollama daemon running the Qwen 2.5 1.5B (or similar) model. This guarantees absolute zero-latency "
        "operations where sensitive data never leaves the chassis."
    )
    pdf.chapter_body(ollama_desc)

    # -----------------------------
    # 3. ADVANCED NLP PARSING
    # -----------------------------
    pdf.add_page()
    pdf.chapter_title('3. Advanced NLP Command Parsing Engine')
    nlp_desc = (
        "Before feeding an instruction to the LLM-which takes time-Phase-5 utilizes a hyper-optimized Regular Expressions (Regex) "
        "engine paired with fuzzy string matching. This system intercepts task-oriented commands locally, interpreting intent instantly "
        "and securely bypassing the AI for pure system commands."
    )
    pdf.chapter_body(nlp_desc)
    
    pdf.bullet_point("Fuzzy Matcher", "Corrects typos automatically (e.g., 'shutdwon' -> 'shutdown', 'opne' -> 'open').")
    pdf.bullet_point("Extractive Regex", "Identifies complex payload strings within casual sentences.")
    
    pdf.chapter_body("Example syntax parsed by the system:")
    pdf.code_block(
        "\"open youtube.com in chrome\"\n"
        "   -> Parsed: ('open_url', 'youtube.com|chrome')\n\n"
        "\"copy final_report.docx to Desktop\"\n"
        "   -> Parsed: ('copy_file', 'final_report.docx|Desktop')\n\n"
        "\"send an email to boss subject Status body Done\"\n"
        "   -> Parsed: ('email', 'boss|Status|Done')"
    )

    # -----------------------------
    # 4. DEEP OS INTEGRATION
    # -----------------------------
    pdf.chapter_title('4. Deep Operating System Integration')
    os_desc = (
        "Phase-5 extends deeply into the Windows operating system using ctypes, pycaw, and the Win32 API. "
        "It executes actions that typically demand specialized software."
    )
    pdf.chapter_body(os_desc)
    
    pdf.sub_title("4.1. Hardware & Power Management")
    pdf.bullet_point("Audio Interfaces", "Manipulates endpoints via pycaw to dynamically set volume percentages or toggle mute.")
    pdf.bullet_point("WMI Brightness", "Uses the Windows Management Instrumentation (WMI) to throttle display dimming.")
    pdf.bullet_point("Power States", "Invokes ctypes.windll user/powrprof functions to instantly sleep, lock, or initiate standard shutdowns.")
    pdf.ln(3)
    
    pdf.sub_title("4.2. Universal Application Control")
    pdf.bullet_point("Smart Launching", "The assistant scans known Registry paths and Start Menu directories to locate almost any installed application globally.")
    pdf.bullet_point("Process Termination", "Leverages psutil to safely SIGTERM processes using soft name matching (e.g., 'close word' terminates WINWORD.EXE).")
    pdf.ln(3)

    # -----------------------------
    # 5. COMMUNICATIONS AUTOMATION
    # -----------------------------
    pdf.add_page()
    pdf.chapter_title('5. Communications Automation')
    comm_desc = (
        "A hallmark capability of Phase-5 is bridging desktop software with online communication. The assistant "
        "manipulates browser states and desktop application handles to perform human-like messaging."
    )
    pdf.chapter_body(comm_desc)
    
    pdf.sub_title("5.1. WhatsApp Desktop Protocol")
    wa_desc = (
        "By interpreting commands like 'send a whatsapp to Athul saying hi', Phase-5 launches the native WhatsApp Windows UI. "
        "It mathematically calculates GUI scale, invokes precise `pyautogui` keyboard events to search for the specific contact, "
        "tabs into the message box, types the dictated text, and hits send. All actions run autonomously on the user's screen."
    )
    pdf.chapter_body(wa_desc)
    
    pdf.sub_title("5.2. Multi-Browser Gmail Compose")
    em_desc = (
        "Phase-5 detects the host's installed browsers (Edge, Chrome, Brave) and exposes an interactive dialog. Once an account "
        "is selected, it orchestrates a specialized Google Mail URL payload to instantly scaffold a draft containing the exact target, "
        "subject line, and body content derived from natural language. It then enforces window activation via `SetForegroundWindow` and "
        "mechanically fires a 'Ctrl + Enter' shortcut to bypass the Compose screen entirely, sending the email hands-free."
    )
    pdf.chapter_body(em_desc)

    # -----------------------------
    # 6. SYSTEM STACK & UI
    # -----------------------------
    pdf.chapter_title('6. Technology Stack & Interface')
    ui_desc = (
        "The interface relies on PyQt6 to render a modern, dark-themed 'hacker styled' console. It features asynchronous QThread "
        "handlers that ensure the GUI remains fluid while complex AI models calculate responses or system diagnostic tasks run in "
        "the background memory."
    )
    pdf.chapter_body(ui_desc)
    
    pdf.bullet_point("Core Programming Language", "Python 3.10+ (Static Type Checked)")
    pdf.bullet_point("GUI Architecture", "PyQt6 (Signals, Slots, Asynchronous Event Loops)")
    pdf.bullet_point("AI Routing Frameworks", "Groq SDK, PyOllama")
    pdf.bullet_point("System Hooking", "win32gui, win32con, ctypes, psutil, pycaw")
    pdf.bullet_point("GUI Automation", "pyautogui, subprocess, webbrowser")
    
    # -----------------------------
    # 7. FUTURE ROADMAP
    # -----------------------------
    pdf.add_page()
    pdf.chapter_title('7. Future Vision & Roadmap')
    fut_desc = (
        "Phase-5 is rapidly expanding. Future implementations will transition the interface into a multimodal agent:"
    )
    pdf.chapter_body(fut_desc)
    
    pdf.bullet_point("Local Voice Recognition", "Native integration of OpenAI Whisper locally running on GPU to accept dictation offline.")
    pdf.bullet_point("Optical Character Recognition (OCR)", "Directly reading screen contents (images, un-copyable text) for context-aware queries.")
    pdf.bullet_point("Task Scheduler", "Natural language chronological workflows (e.g., 'Turn off wifi at 10 PM and lock screen').")
    pdf.bullet_point("Agentic Browser Control", "Automated web scraping and web navigation using headless Playwright integrations.")
    
    pdf.ln(10)
    pdf.set_font('helvetica', 'I', 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, 'Phase-5 : Built to redefine private desktop autonomy.', align='C')

    # Output
    out_path = os.path.join(os.getcwd(), 'Phase-5_Deeply_Detailed_Project_Report.pdf')
    pdf.output(out_path)
    print("PDF successfully generated at:", out_path)

if __name__ == '__main__':
    create_pdf()
