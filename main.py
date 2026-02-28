"""
The Counsel — Multi-Agent Decision Engine  v3
CustomTkinter + Backboard.io

Setup:
    1. pip install customtkinter Pillow requests
    2. Run setup_agents.py once → paste the three IDs below
    3. Set BACKBOARD_API_KEY environment variable (or paste directly)
    4. python main.py
"""

import customtkinter as ctk
import threading
import requests
import json
import os
import time
from datetime import datetime

# ── Appearance ────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ── Palette ───────────────────────────────────────────────────────────────────
BG_ROOT   = "#080809"
BG_PANEL  = "#0F0F12"
BG_CARD   = "#131318"
BG_INPUT  = "#18181F"
BG_HOVER  = "#1E1E28"
BORDER    = "#242432"
BORDER_LT = "#2E2E42"

GEMINI_C  = "#38BDF8"   # sky blue
CLAUDE_C  = "#F472B6"   # pink
GPT_C     = "#6EE7B7"   # emerald

ACCENT    = "#6366F1"   # violet
ACCENT_HV = "#4F46E5"
GOLD      = "#FBBF24"
RED_SOFT  = "#F87171"
TEXT_HI   = "#F1F5F9"
TEXT_MID  = "#94A3B8"
TEXT_DIM  = "#475569"

# ── Typography ────────────────────────────────────────────────────────────────
# Response panels — clean sans-serif instead of Courier
FONT_BODY    = ("Segoe UI",      12)
FONT_BODY_SM = ("Segoe UI",      11)
FONT_MONO    = ("Consolas",      11)   # only used for session ID / status chips
FONT_LABEL   = ("Segoe UI",      10, "bold")
FONT_HEADING = ("Segoe UI",      13, "bold")
FONT_TITLE   = ("Segoe UI",      18, "bold")

# ── Response Length Presets ───────────────────────────────────────────────────
# Appended as an instruction to each agent's prompt.
LENGTH_PRESETS = {
    "Concise   — 1-2 paragraphs": (
        "Keep your response concise: 1-2 short paragraphs maximum. "
        "Lead with the most important point. Cut everything else."
    ),
    "Standard  — 3-4 paragraphs": (
        "Keep your response to 3-4 paragraphs. Be thorough but focused. "
        "No padding or filler."
    ),
    "Detailed  — full analysis": (
        "Provide a full, detailed analysis. Use structure and depth. "
        "Cover all relevant angles without artificial brevity."
    ),
    "Executive — bullet points": (
        "Format your response as a tight executive brief: "
        "one sentence summary, then 4-6 bullet points only. No prose."
    ),
}

# ── Personality Presets ───────────────────────────────────────────────────────
TECHNICIAN_PERSONALITIES = {
    "Default — The Technician": (
        "You are a rapid analytical engine. Focus on raw data, metrics, and operational "
        "efficiency. Be direct and structured."
    ),
    "Quantitative Trader": (
        "You are a quantitative analyst. Frame everything in probabilities, expected value, "
        "and risk-adjusted returns. Use numbers wherever possible. Be terse."
    ),
    "Military Strategist": (
        "You are a military strategist. Use frameworks: objectives, lines of effort, "
        "center of gravity, critical vulnerabilities. Be decisive and structured."
    ),
    "Silicon Valley Engineer": (
        "You are a senior engineer at a top tech company. Think in systems, scalability, "
        "and velocity. Use engineering frameworks. Be opinionated and fast."
    ),
    "Management Consultant": (
        "You are a McKinsey-trained consultant. Use MECE frameworks and executive summaries. "
        "Lead with the recommendation, support with data."
    ),
}

AUDITOR_PERSONALITIES = {
    "Default — The Auditor": (
        "You are a risk auditor and adversarial critic. Find flaws, blind spots, and safety "
        "risks in the analysis given to you. Be thorough and adversarial."
    ),
    "Devil's Advocate": (
        "You are a professional devil's advocate. Steelman the opposite position and dismantle "
        "every assumption. Be intellectually aggressive."
    ),
    "Regulatory Inspector": (
        "You are a compliance officer. Examine every claim for legal exposure, regulatory risk, "
        "and governance failures. Be methodical and conservative."
    ),
    "Paranoid CISO": (
        "You are a CISO with extreme threat awareness. Every plan has an attack surface. "
        "Find every security risk and failure mode. Assume adversarial conditions."
    ),
    "Venture Skeptic": (
        "You are a famously skeptical VC. Poke holes in every assumption. What is the "
        "worst-case scenario? Be blunt and commercially ruthless."
    ),
}

CHAIRMAN_PERSONALITIES = {
    "Default — The Chairman": (
        "You are the Chairman of a multi-agent council. Synthesize both agents and issue "
        "a final binding ruling. Begin with 'Consensus Reached:' or 'Deadlock:'."
    ),
    "Stoic Judge": (
        "You are a stoic federal judge. Weigh evidence dispassionately. Cite the strongest "
        "arguments from both sides. Begin with 'Consensus Reached:' or 'Deadlock:'."
    ),
    "Wartime General": (
        "You are a wartime general under pressure. Cut through debate, commit to a course "
        "of action, issue clear orders. Begin with 'Consensus Reached:' or 'Deadlock:'."
    ),
    "Boardroom CEO": (
        "You are a Fortune 500 CEO. Synthesize into a shareholder-ready decision with "
        "clear rationale and next steps. Begin with 'Consensus Reached:' or 'Deadlock:'."
    ),
    "Socratic Philosopher": (
        "You are a Socratic philosopher. Find the deeper question, then issue your verdict "
        "with intellectual humility. Begin with 'Consensus Reached:' or 'Deadlock:'."
    ),
}

# ── Backboard Config ──────────────────────────────────────────────────────────
TECHNICIAN_ID = "6e7216bd-be63-40a3-b39f-085f1794aa37"
AUDITOR_ID    = "75aed7a6-d7de-4a8d-8a9f-bbab7c419a62"
CHAIRMAN_ID   = "8d69dbe7-5b4b-48e7-9f89-6311438273dd"

API_KEY  = os.environ.get("BACKBOARD_API_KEY", "")
BASE_URL = "https://app.backboard.io/api"

TECHNICIAN_PROVIDER = "google"
TECHNICIAN_MODEL    = "gemini-2.5-flash"
AUDITOR_PROVIDER    = "anthropic"
AUDITOR_MODEL       = "claude-sonnet-4-20250514"
CHAIRMAN_PROVIDER   = "openai"
CHAIRMAN_MODEL      = "gpt-4o"

USE_MOCK = not API_KEY or "PASTE" in TECHNICIAN_ID


# ── Backboard REST Client ─────────────────────────────────────────────────────
class BackboardClient:
    def __init__(self):
        self.headers = {"X-API-Key": API_KEY}

    def create_thread(self, assistant_id: str) -> str:
        r = requests.post(
            f"{BASE_URL}/assistants/{assistant_id}/threads",
            json={}, headers=self.headers
        )
        r.raise_for_status()
        return r.json()["thread_id"]

    def send_message_stream(self, thread_id, content, llm_provider,
                             model_name, memory, on_chunk):
        r = requests.post(
            f"{BASE_URL}/threads/{thread_id}/messages",
            headers=self.headers,
            data={"content": content, "stream": "true", "memory": memory,
                  "llm_provider": llm_provider, "model_name": model_name},
            stream=True
        )
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            line = line.decode("utf-8")
            if line.startswith("data: "):
                line = line[6:]
            if line in ("[DONE]", ""):
                continue
            try:
                chunk = json.loads(line)
                if chunk.get("type") == "content_streaming":
                    text = chunk.get("content", "")
                    if text:
                        on_chunk(text)
            except json.JSONDecodeError:
                continue


# ── Mock Client ───────────────────────────────────────────────────────────────
class MockClient:
    def create_thread(self, assistant_id):
        return "mock-thread-id"

    def send_message_stream(self, thread_id, content, llm_provider,
                             model_name, memory, on_chunk):
        responses = {
            "google": (
                "ANALYSIS — The Technician\n\n"
                "Processing with high-velocity pattern recognition.\n\n"
                "Key findings: Throughput metrics show a 34% efficiency delta against baseline. "
                "Primary bottleneck is third-party integration latency at 420ms average. "
                "Dataset confidence sits at 91.2% with an anomaly flag on the Q3 outlier cluster.\n\n"
                "Recommendation: Parallel-process the pipeline, eliminate synchronous blocking "
                "calls, and deploy an edge caching layer.\n\n"
                "Speed: FAST  ·  Risk: LOW  ·  Confidence: HIGH"
            ),
            "anthropic": (
                "AUDIT REPORT — The Auditor\n\n"
                "Reviewing the Technician's output for blind spots and failure modes.\n\n"
                "Concern 1: The 91.2% confidence figure ignores the 8.8% tail risk — in "
                "high-stakes environments that margin can be catastrophic.\n\n"
                "Concern 2: Edge caching introduces stale-data risk if the invalidation "
                "strategy is undefined. Concern 3: Parallel processing without concurrency "
                "controls risks race conditions. Concern 4: No rollback plan specified.\n\n"
                "Verdict: Operationally sound in 91% of scenarios but lacks defensive "
                "architecture. Mandatory circuit-breakers and staged rollout required.\n\n"
                "Risk: MEDIUM  ·  Safety Posture: NEEDS HARDENING"
            ),
            "openai": (
                "Consensus Reached: The council has reached a structured agreement.\n\n"
                "The core recommendation — parallel processing with edge caching — is approved "
                "with the Auditor's safety controls embedded as mandatory requirements.\n\n"
                "ADOPT: Parallel pipeline architecture and edge caching layer.\n"
                "REQUIRE: Circuit-breaker pattern on all external calls.\n"
                "REQUIRE: Staged rollout at 10% → 50% → 100% traffic.\n"
                "DEFER: Full deployment until stale-data invalidation is defined.\n\n"
                "Timeline: 2-week phased rollout. Risk posture: MANAGED.\n\n"
                "— The Counsel has spoken."
            )
        }
        text = responses.get(llm_provider, "Mock response.")
        for char in text:
            on_chunk(char)
            time.sleep(0.006)


# ── Chip Widget — small coloured status pill ──────────────────────────────────
class StatusChip(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_HOVER, corner_radius=4,
                         height=22, **kwargs)
        self.pack_propagate(False)
        self._lbl = ctk.CTkLabel(self, text="STANDBY", font=("Consolas", 9),
                                  text_color=TEXT_DIM)
        self._lbl.pack(padx=8, pady=0)

    def set(self, text, color=TEXT_DIM):
        self._lbl.configure(text=text, text_color=color)


# ── Agent Panel ───────────────────────────────────────────────────────────────
class AgentPanel(ctk.CTkFrame):
    def __init__(self, master, title, model_label, color, **kwargs):
        super().__init__(master, fg_color=BG_CARD, corner_radius=10,
                         border_width=1, border_color=BORDER, **kwargs)
        self.color = color

        # ── Header ──
        hdr = ctk.CTkFrame(self, fg_color="transparent", height=52)
        hdr.pack(fill="x", padx=14, pady=(12, 0))
        hdr.pack_propagate(False)

        # Accent dot
        ctk.CTkFrame(hdr, fg_color=color, width=3, height=28,
                     corner_radius=2).pack(side="left", padx=(0, 10), pady=12)

        label_col = ctk.CTkFrame(hdr, fg_color="transparent")
        label_col.pack(side="left", fill="y", pady=8)
        ctk.CTkLabel(label_col, text=title, font=FONT_HEADING,
                     text_color=TEXT_HI).pack(anchor="w")
        ctk.CTkLabel(label_col, text=model_label, font=FONT_BODY_SM,
                     text_color=TEXT_DIM).pack(anchor="w")

        self.chip = StatusChip(hdr)
        self.chip.pack(side="right", pady=14)

        # ── Divider ──
        ctk.CTkFrame(self, fg_color=BORDER, height=1).pack(fill="x", padx=14)

        # ── Text area ──
        self.text_box = ctk.CTkTextbox(
            self,
            font=FONT_BODY,
            fg_color="transparent",
            text_color=TEXT_MID,
            corner_radius=0,
            wrap="word",
            state="disabled",
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=BORDER_LT,
            activate_scrollbars=True,
        )
        self.text_box.pack(fill="both", expand=True, padx=4, pady=(4, 8))

    def set_status(self, text, color):
        self.chip.set(text, color)

    def clear(self):
        self.text_box.configure(state="normal")
        self.text_box.delete("1.0", "end")
        self.text_box.configure(state="disabled")
        self.chip.set("STANDBY", TEXT_DIM)

    def append(self, text):
        self.text_box.configure(state="normal")
        self.text_box.insert("end", text)
        self.text_box.see("end")
        self.text_box.configure(state="disabled")


# ── Segmented Control (response length) ──────────────────────────────────────
class SegmentedRow(ctk.CTkFrame):
    """A row of toggle buttons acting as a single-select control."""
    def __init__(self, master, options, callback=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._btns = {}
        self._selected = ctk.StringVar(value=options[0])
        self._cb = callback

        for opt in options:
            b = ctk.CTkButton(
                self, text=opt,
                font=("Segoe UI", 10),
                fg_color=ACCENT if opt == options[0] else BG_INPUT,
                hover_color=ACCENT_HV,
                text_color=TEXT_HI if opt == options[0] else TEXT_DIM,
                corner_radius=5,
                height=28,
                border_width=1,
                border_color=BORDER_LT if opt != options[0] else ACCENT,
                command=lambda o=opt: self._select(o),
            )
            b.pack(side="left", padx=(0, 4))
            self._btns[opt] = b

    def _select(self, opt):
        for o, b in self._btns.items():
            active = (o == opt)
            b.configure(
                fg_color=ACCENT if active else BG_INPUT,
                text_color=TEXT_HI if active else TEXT_DIM,
                border_color=ACCENT if active else BORDER_LT,
            )
        self._selected.set(opt)
        if self._cb:
            self._cb(opt)

    def get(self):
        return self._selected.get()


# ── Main Application ──────────────────────────────────────────────────────────
class CounselApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("The Counsel")
        self.geometry("1480x940")
        self.minsize(1100, 740)
        self.configure(fg_color=BG_ROOT)

        self.client = MockClient() if USE_MOCK else BackboardClient()
        self._running = False
        self._log_data = []

        self._build_ui()

        if USE_MOCK:
            self._set_status("MOCK MODE  —  paste your API key and agent IDs into main.py")

    # ── UI Construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        self._build_topbar()
        self._build_input_section()
        self._build_settings_panel()
        self._build_agent_panels()
        self._build_consensus_section()
        self._build_statusbar()

    def _build_topbar(self):
        bar = ctk.CTkFrame(self, fg_color=BG_PANEL, height=52, corner_radius=0)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        # Left — wordmark
        left = ctk.CTkFrame(bar, fg_color="transparent")
        left.pack(side="left", padx=20, pady=0, fill="y")

        ctk.CTkLabel(left, text="THE COUNSEL",
                     font=("Segoe UI", 15, "bold"),
                     text_color=TEXT_HI).pack(side="left", pady=16)
        ctk.CTkLabel(left, text=" · Multi-Agent Decision Engine",
                     font=("Segoe UI", 12),
                     text_color=TEXT_DIM).pack(side="left", pady=16)

        # Right — session chip
        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.pack(side="right", padx=20, fill="y")

        self.session_chip = StatusChip(right)
        self.session_chip.pack(side="right", pady=15)

        # Bottom border
        ctk.CTkFrame(self, fg_color=BORDER, height=1).pack(fill="x")

    def _build_input_section(self):
        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.pack(fill="x", padx=20, pady=(16, 0))

        # Left — prompt label + box
        left = ctk.CTkFrame(wrap, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(left, text="QUERY", font=FONT_LABEL,
                     text_color=TEXT_DIM).pack(anchor="w", pady=(0, 6))

        self.prompt_box = ctk.CTkTextbox(
            left, height=76,
            font=("Segoe UI", 13),
            fg_color=BG_INPUT,
            text_color=TEXT_HI,
            border_color=BORDER_LT,
            border_width=1,
            corner_radius=8,
            wrap="word",
        )
        self.prompt_box.pack(fill="x")
        self.prompt_box.insert("1.0",
            "We are considering a major infrastructure overhaul. "
            "Should we migrate our entire data pipeline to microservices this quarter?"
        )
        self.prompt_box.bind("<Control-Return>", lambda e: self._convene())

        # Right — convene button
        right = ctk.CTkFrame(wrap, fg_color="transparent", width=160)
        right.pack(side="right", padx=(16, 0), fill="y")
        right.pack_propagate(False)

        ctk.CTkLabel(right, text="", font=FONT_LABEL).pack(pady=(0, 6))  # spacer

        self.convene_btn = ctk.CTkButton(
            right,
            text="Convene Counsel",
            font=("Segoe UI", 13, "bold"),
            fg_color=ACCENT,
            hover_color=ACCENT_HV,
            text_color=TEXT_HI,
            corner_radius=8,
            height=76,
            command=self._convene,
        )
        self.convene_btn.pack(fill="x")

    def _build_settings_panel(self):
        """Collapsible settings bar: personality dropdowns + response length."""
        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill="x", padx=20, pady=(10, 0))

        # Toggle row
        toggle_row = ctk.CTkFrame(outer, fg_color="transparent")
        toggle_row.pack(fill="x")

        self._settings_open = False
        self._settings_body = ctk.CTkFrame(
            outer, fg_color=BG_PANEL, corner_radius=8,
            border_width=1, border_color=BORDER
        )

        def toggle():
            if self._settings_open:
                self._settings_body.pack_forget()
                self._toggle_btn.configure(text="▶  Configure Session")
                self._settings_open = False
            else:
                self._settings_body.pack(fill="x", pady=(6, 0))
                self._toggle_btn.configure(text="▼  Configure Session")
                self._settings_open = True

        self._toggle_btn = ctk.CTkButton(
            toggle_row,
            text="▶  Configure Session",
            font=("Segoe UI", 10, "bold"),
            fg_color="transparent",
            hover_color=BG_HOVER,
            text_color=TEXT_DIM,
            anchor="w",
            width=180,
            height=26,
            corner_radius=5,
            command=toggle,
        )
        self._toggle_btn.pack(side="left")

        ctk.CTkLabel(toggle_row,
                     text="Personality · Response Length  (Ctrl+Enter to convene)",
                     font=("Segoe UI", 10), text_color=TEXT_DIM).pack(side="left", padx=6)

        # ── Settings body ──
        body_inner = ctk.CTkFrame(self._settings_body, fg_color="transparent")
        body_inner.pack(fill="x", padx=16, pady=12)

        # Section: Personalities
        ctk.CTkLabel(body_inner, text="AGENT PERSONALITIES",
                     font=FONT_LABEL, text_color=TEXT_DIM).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 8)
        )
        body_inner.columnconfigure((0, 1, 2), weight=1)

        def make_dropdown(parent, label, color, options, row, col):
            cell = ctk.CTkFrame(parent, fg_color="transparent")
            cell.grid(row=row, column=col, sticky="ew",
                      padx=(0 if col == 0 else 10, 0), pady=(0, 4))

            hdr = ctk.CTkFrame(cell, fg_color="transparent")
            hdr.pack(fill="x", pady=(0, 4))
            ctk.CTkFrame(hdr, fg_color=color, width=3, height=12,
                         corner_radius=1).pack(side="left", padx=(0, 5))
            ctk.CTkLabel(hdr, text=label, font=("Segoe UI", 10, "bold"),
                         text_color=color).pack(side="left")

            var = ctk.StringVar(value=list(options.keys())[0])
            ctk.CTkOptionMenu(
                cell,
                values=list(options.keys()),
                variable=var,
                fg_color=BG_INPUT,
                button_color=BORDER_LT,
                button_hover_color=ACCENT,
                dropdown_fg_color=BG_CARD,
                dropdown_hover_color=BG_HOVER,
                text_color=TEXT_MID,
                font=("Segoe UI", 11),
                corner_radius=6,
                height=32,
            ).pack(fill="x")
            return var

        self._tech_personality  = make_dropdown(
            body_inner, "TECHNICIAN", GEMINI_C, TECHNICIAN_PERSONALITIES, 1, 0)
        self._audit_personality = make_dropdown(
            body_inner, "AUDITOR",    CLAUDE_C, AUDITOR_PERSONALITIES,    1, 1)
        self._chair_personality = make_dropdown(
            body_inner, "CHAIRMAN",   GPT_C,    CHAIRMAN_PERSONALITIES,   1, 2)

        # Divider
        ctk.CTkFrame(body_inner, fg_color=BORDER, height=1).grid(
            row=2, column=0, columnspan=3, sticky="ew", pady=(12, 10))

        # Section: Response Length
        ctk.CTkLabel(body_inner, text="RESPONSE LENGTH",
                     font=FONT_LABEL, text_color=TEXT_DIM).grid(
            row=3, column=0, columnspan=3, sticky="w", pady=(0, 8))

        length_row = ctk.CTkFrame(body_inner, fg_color="transparent")
        length_row.grid(row=4, column=0, columnspan=3, sticky="w")

        # Short display labels for the segmented control
        length_labels = ["Concise", "Standard", "Detailed", "Executive"]
        self._length_seg = SegmentedRow(length_row, length_labels)
        self._length_seg.pack(side="left")

        # Map short labels → full preset keys
        self._length_map = {
            "Concise":   "Concise   — 1-2 paragraphs",
            "Standard":  "Standard  — 3-4 paragraphs",
            "Detailed":  "Detailed  — full analysis",
            "Executive": "Executive — bullet points",
        }

    def _build_agent_panels(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=(14, 0))
        frame.columnconfigure((0, 1, 2), weight=1)
        frame.rowconfigure(0, weight=1)

        self.gemini_panel = AgentPanel(
            frame,
            title="The Technician",
            model_label="Gemini Flash  ·  Speed & Data",
            color=GEMINI_C,
        )
        self.gemini_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 7))

        self.claude_panel = AgentPanel(
            frame,
            title="The Auditor",
            model_label="Claude Sonnet  ·  Risk & Safety",
            color=CLAUDE_C,
        )
        self.claude_panel.grid(row=0, column=1, sticky="nsew", padx=3)

        self.gpt_panel = AgentPanel(
            frame,
            title="The Chairman",
            model_label="GPT-4o  ·  Synthesis & Ruling",
            color=GPT_C,
        )
        self.gpt_panel.grid(row=0, column=2, sticky="nsew", padx=(7, 0))

    def _build_consensus_section(self):
        outer = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10,
                              border_width=1, border_color=BORDER)
        outer.pack(fill="x", padx=20, pady=(10, 0))

        # Header row
        hdr = ctk.CTkFrame(outer, fg_color="transparent", height=44)
        hdr.pack(fill="x", padx=14)
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text="Final Consensus", font=FONT_HEADING,
                     text_color=GOLD).pack(side="left", pady=10)

        self.verdict_chip = StatusChip(hdr)
        self.verdict_chip.pack(side="left", padx=10, pady=11)

        ctk.CTkButton(
            hdr, text="Save Log",
            font=("Segoe UI", 10),
            fg_color="transparent",
            hover_color=BG_HOVER,
            text_color=TEXT_DIM,
            border_color=BORDER_LT,
            border_width=1,
            corner_radius=5,
            width=80, height=26,
            command=self._save_log,
        ).pack(side="right", pady=9)

        ctk.CTkFrame(outer, fg_color=BORDER, height=1).pack(fill="x", padx=14)

        self.consensus_box = ctk.CTkTextbox(
            outer,
            height=100,
            font=FONT_BODY,
            fg_color="transparent",
            text_color=GOLD,
            corner_radius=0,
            wrap="word",
            state="disabled",
            scrollbar_button_color=BORDER,
        )
        self.consensus_box.pack(fill="x", padx=4, pady=(4, 8))

    def _build_statusbar(self):
        ctk.CTkFrame(self, fg_color=BORDER, height=1).pack(fill="x")
        bar = ctk.CTkFrame(self, fg_color=BG_PANEL, height=30, corner_radius=0)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self.status_bar = ctk.CTkLabel(
            bar,
            text="Ready  —  Ctrl+Enter or click Convene Counsel to begin",
            font=("Segoe UI", 10),
            text_color=TEXT_DIM,
            anchor="w",
        )
        self.status_bar.pack(side="left", padx=14)

    # ── Thread-safe UI helpers ────────────────────────────────────────────────
    def _ui(self, fn):
        self.after(0, fn)

    def _set_status(self, text):
        self._ui(lambda: self.status_bar.configure(text=text))

    def _card_append(self, panel, text):
        self._ui(lambda: panel.append(text))

    def _card_status(self, panel, text, color):
        self._ui(lambda: panel.set_status(text, color))

    def _consensus_append(self, text):
        def _do():
            self.consensus_box.configure(state="normal")
            self.consensus_box.insert("end", text)
            self.consensus_box.see("end")
            self.consensus_box.configure(state="disabled")
        self._ui(_do)

    def _set_verdict(self, text, color):
        self._ui(lambda: self.verdict_chip.set(text, color))

    def _session_done(self):
        self._ui(lambda: self.convene_btn.configure(
            state="normal", text="Convene Counsel"
        ))

    # ── Convene ───────────────────────────────────────────────────────────────
    def _convene(self):
        if self._running:
            return
        prompt = self.prompt_box.get("1.0", "end").strip()
        if not prompt:
            self._set_status("Please enter a query before convening the counsel.")
            return

        self._running = True
        self.convene_btn.configure(state="disabled", text="In Session…")
        self._log_data = []

        sid = datetime.now().strftime("SES-%H%M%S")
        self.session_chip.set(sid, TEXT_DIM)

        for panel in [self.gemini_panel, self.claude_panel, self.gpt_panel]:
            panel.clear()

        self.consensus_box.configure(state="normal")
        self.consensus_box.delete("1.0", "end")
        self.consensus_box.configure(state="disabled")
        self.verdict_chip.set("DELIBERATING…", TEXT_DIM)

        threading.Thread(target=self._run_session, args=(prompt,), daemon=True).start()

    def _run_session(self, prompt: str):
        # Read all settings synchronously before handing off to background
        tech_persona  = TECHNICIAN_PERSONALITIES[self._tech_personality.get()]
        audit_persona = AUDITOR_PERSONALITIES[self._audit_personality.get()]
        chair_persona = CHAIRMAN_PERSONALITIES[self._chair_personality.get()]

        length_key    = self._length_map[self._length_seg.get()]
        length_instr  = LENGTH_PRESETS[length_key]

        try:
            # ── Phase 1: The Technician ───────────────────────────────────────
            self._set_status("Phase 1 / 3  ·  Technician analyzing…")
            self._card_status(self.gemini_panel, "PROCESSING", GEMINI_C)

            t1 = self.client.create_thread(TECHNICIAN_ID)
            gemini_out = []

            def on_gemini(chunk):
                gemini_out.append(chunk)
                self._card_append(self.gemini_panel, chunk)

            self.client.send_message_stream(
                thread_id=t1,
                content=(
                    f"[ROLE]: {tech_persona}\n"
                    f"[LENGTH]: {length_instr}\n\n"
                    f"[QUERY]: {prompt}"
                ),
                llm_provider=TECHNICIAN_PROVIDER,
                model_name=TECHNICIAN_MODEL,
                memory="Auto",
                on_chunk=on_gemini,
            )
            self._card_status(self.gemini_panel, "COMPLETE", GEMINI_C)
            gemini_text = "".join(gemini_out)
            self._log_data.append((
                f"THE TECHNICIAN  [{self._tech_personality.get()}  ·  {self._length_seg.get()}]",
                gemini_text
            ))

            # ── Phase 2: The Auditor ──────────────────────────────────────────
            self._set_status("Phase 2 / 3  ·  Auditor reviewing…")
            self._card_status(self.claude_panel, "AUDITING", CLAUDE_C)

            t2 = self.client.create_thread(AUDITOR_ID)
            claude_out = []

            def on_claude(chunk):
                claude_out.append(chunk)
                self._card_append(self.claude_panel, chunk)

            self.client.send_message_stream(
                thread_id=t2,
                content=(
                    f"[ROLE]: {audit_persona}\n"
                    f"[LENGTH]: {length_instr}\n\n"
                    f"Original query: {prompt}\n\n"
                    f"Technician's analysis:\n{gemini_text}\n\n"
                    f"Audit the above for risks, blind spots, unstated assumptions, "
                    f"and safety concerns. Be adversarial and thorough."
                ),
                llm_provider=AUDITOR_PROVIDER,
                model_name=AUDITOR_MODEL,
                memory="Auto",
                on_chunk=on_claude,
            )
            self._card_status(self.claude_panel, "COMPLETE", CLAUDE_C)
            claude_text = "".join(claude_out)
            self._log_data.append((
                f"THE AUDITOR  [{self._audit_personality.get()}  ·  {self._length_seg.get()}]",
                claude_text
            ))

            # ── Phase 3: The Chairman ─────────────────────────────────────────
            self._set_status("Phase 3 / 3  ·  Chairman deliberating…")
            self._card_status(self.gpt_panel, "DELIBERATING", GPT_C)

            t3 = self.client.create_thread(CHAIRMAN_ID)
            gpt_out = []

            def on_gpt(chunk):
                gpt_out.append(chunk)
                self._card_append(self.gpt_panel, chunk)
                self._consensus_append(chunk)

            self.client.send_message_stream(
                thread_id=t3,
                content=(
                    f"[ROLE]: {chair_persona}\n"
                    f"[LENGTH]: {length_instr}\n\n"
                    f"Original query: {prompt}\n\n"
                    f"Technician's analysis:\n{gemini_text}\n\n"
                    f"Auditor's critique:\n{claude_text}\n\n"
                    f"Synthesize both positions and issue your final ruling. "
                    f"You MUST begin with exactly 'Consensus Reached:' or 'Deadlock:'. "
                    f"Deadlock should be rare — most positions can be reconciled."
                ),
                llm_provider=CHAIRMAN_PROVIDER,
                model_name=CHAIRMAN_MODEL,
                memory="Auto",
                on_chunk=on_gpt,
            )
            self._card_status(self.gpt_panel, "COMPLETE", GPT_C)
            gpt_text = "".join(gpt_out)
            self._log_data.append((
                f"THE CHAIRMAN  [{self._chair_personality.get()}  ·  {self._length_seg.get()}]",
                gpt_text
            ))

            # ── Verdict ───────────────────────────────────────────────────────
            low = gpt_text.strip().lower()
            if low.startswith("consensus reached"):
                self._set_verdict("CONSENSUS REACHED", GPT_C)
            elif low.startswith("deadlock"):
                self._set_verdict("DEADLOCK", RED_SOFT)
            else:
                self._set_verdict("RULING ISSUED", GOLD)

            self._set_status("Session complete  ·  The Counsel has spoken.")

        except requests.HTTPError as e:
            self._set_status(f"API error {e.response.status_code}  —  {e.response.text[:100]}")
        except Exception as e:
            self._set_status(f"Error: {e}")
        finally:
            self._running = False
            self._session_done()

    # ── Save Log ──────────────────────────────────────────────────────────────
    def _save_log(self):
        if not self._log_data:
            self._set_status("Nothing to save yet.")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"counsel_log_{ts}.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write("=" * 72 + "\n")
            f.write("THE COUNSEL — SESSION LOG\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 72 + "\n\n")
            for agent, content in self._log_data:
                f.write(f"[ {agent} ]\n")
                f.write("─" * 52 + "\n")
                f.write(content.strip() + "\n\n")
        self._set_status(f"Log saved  →  {path}")


# ── Entry ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = CounselApp()
    app.mainloop()
