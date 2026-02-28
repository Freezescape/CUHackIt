"""
The Counsel — Multi-Agent Decision Engine
A dark-themed industrial desktop app powered by CustomTkinter + Backboard.io

Setup:
    1. pip install customtkinter Pillow requests
    2. Run setup_agents.py once to create your agents and get their IDs
    3. Paste the three IDs into the AGENT IDs section below
    4. Set your BACKBOARD_API_KEY environment variable
    5. python main.py
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

# ── Color Palette ─────────────────────────────────────────────────────────────
BG_DEEP  = "#0D0D0F"
BG_PANEL = "#141416"
BG_CARD  = "#1A1A1E"
BG_INPUT = "#1E1E24"
BORDER   = "#2A2A35"

GEMINI_C  = "#4FC3F7"
CLAUDE_C  = "#F06292"
GPT_C     = "#A5D6A7"

ACCENT    = "#5C6BC0"
CONSENSUS = "#FFD54F"
TEXT_DIM  = "#6B7280"
TEXT_MAIN = "#E8EAF0"

FONT_MONO = ("Courier", 12)

# ── Backboard Config ──────────────────────────────────────────────────────────
# Paste your IDs here after running setup_agents.py
TECHNICIAN_ID = "e734432b-dc99-4132-b12b-fef16ff3cb91"
AUDITOR_ID    = "f0d83f5c-3364-4dda-8a8d-43a3c519dc02"
CHAIRMAN_ID   = "11b491ae-f707-4e44-b315-ec85f28f7f34"

API_KEY  = os.environ.get("BACKBOARD_API_KEY", "")
BASE_URL = "https://app.backboard.io/api"

# Model assigned per-message (not per-assistant — this is how Backboard works)
TECHNICIAN_PROVIDER = "google"
TECHNICIAN_MODEL    = "gemini-2.5-flash"

AUDITOR_PROVIDER    = "anthropic"
AUDITOR_MODEL       = "claude-sonnet-4-20250514"

CHAIRMAN_PROVIDER   = "openai"
CHAIRMAN_MODEL      = "gpt-4o"

# ── Set to True to use mock responses (no API key needed) ─────────────────────
USE_MOCK = not API_KEY or "PASTE" in TECHNICIAN_ID


# ── Backboard REST Client ─────────────────────────────────────────────────────
class BackboardClient:
    def __init__(self):
        self.headers = {"X-API-Key": API_KEY}

    def create_thread(self, assistant_id: str) -> str:
        r = requests.post(
            f"{BASE_URL}/assistants/{assistant_id}/threads",
            json={},
            headers=self.headers
        )
        r.raise_for_status()
        return r.json()["thread_id"]

    def send_message_stream(self, thread_id: str, content: str,
                             llm_provider: str, model_name: str,
                             memory: str, on_chunk):
        r = requests.post(
            f"{BASE_URL}/threads/{thread_id}/messages",
            headers=self.headers,
            data={
                "content": content,
                "stream": "true",
                "memory": memory,
                "llm_provider": llm_provider,
                "model_name": model_name,
            },
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


# ── Mock Client (used when no API key / IDs configured) ───────────────────────
class MockClient:
    def create_thread(self, assistant_id: str) -> str:
        return "mock-thread-id"

    def send_message_stream(self, thread_id, content, llm_provider,
                             model_name, memory, on_chunk):
        responses = {
            "google": (
                "ANALYSIS [Technician / Gemini]:\n\n"
                "Processing input with high-velocity pattern recognition...\n\n"
                "Raw Data Assessment:\n"
                "• Throughput metrics indicate a 34% efficiency delta against baseline.\n"
                "• Primary bottleneck: third-party integration latency (avg 420ms).\n"
                "• Dataset confidence: 91.2% — anomaly flag on Q3 outlier cluster.\n\n"
                "Recommended Action: Parallel-process the pipeline. "
                "Eliminate synchronous blocking calls. Deploy edge caching layer.\n\n"
                "Speed index: FAST | Risk flag: LOW | Data completeness: HIGH"
            ),
            "anthropic": (
                "AUDIT REPORT [Auditor / Claude]:\n\n"
                "Reviewing The Technician's output for blind spots and failure modes...\n\n"
                "Identified Concerns:\n"
                "1. The 91.2% confidence figure omits the 8.8% tail risk.\n"
                "2. Edge caching introduces stale-data risk if invalidation is undefined.\n"
                "3. Parallel processing without concurrency controls risks race conditions.\n"
                "4. No rollback plan mentioned — single-point-of-failure exposure.\n\n"
                "Safety Verdict: Operationally sound in 91% of scenarios but lacks "
                "defensive architecture. Recommend circuit-breakers and staged rollout.\n\n"
                "Risk index: MEDIUM | Safety posture: NEEDS HARDENING"
            ),
            "openai": (
                "Consensus Reached: After reviewing both the Technician's speed-driven "
                "analysis and the Auditor's risk assessment, the council agrees.\n\n"
                "Chairman's Ruling:\n"
                "The core recommendation is approved with mandatory modifications:\n\n"
                "ADOPT: Parallel pipeline architecture\n"
                "ADOPT: Edge caching layer\n"
                "REQUIRE: Circuit-breaker pattern on all external calls\n"
                "REQUIRE: Staged rollout — 10% > 50% > 100% traffic\n"
                "DEFER: Full deployment until stale-data invalidation is defined\n\n"
                "Final directive: Proceed with Auditor's safety controls embedded. "
                "Timeline: 2-week phased rollout.\n\n"
                "— The Counsel has spoken."
            )
        }
        text = responses.get(llm_provider, "Mock response.")
        for char in text:
            on_chunk(char)
            time.sleep(0.008)


# ── Agent Card Widget ─────────────────────────────────────────────────────────
class AgentCard(ctk.CTkFrame):
    def __init__(self, master, title, subtitle, color, **kwargs):
        super().__init__(master, fg_color=BG_CARD, corner_radius=8,
                         border_width=1, border_color=BORDER, **kwargs)

        header = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, height=48)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkFrame(header, fg_color=color, width=4,
                     height=32, corner_radius=2).pack(side="left", padx=(10, 8), pady=8)

        info = ctk.CTkFrame(header, fg_color="transparent")
        info.pack(side="left", fill="y", pady=6)
        ctk.CTkLabel(info, text=title, font=("Segoe UI", 12, "bold"),
                     text_color=color).pack(anchor="w")
        ctk.CTkLabel(info, text=subtitle, font=("Segoe UI", 10),
                     text_color=TEXT_DIM).pack(anchor="w")

        self.status_label = ctk.CTkLabel(header, text="● STANDBY",
                                          font=("Segoe UI", 9), text_color=TEXT_DIM)
        self.status_label.pack(side="right", padx=12)

        self.text_box = ctk.CTkTextbox(
            self, font=FONT_MONO, fg_color=BG_INPUT,
            text_color=TEXT_MAIN, corner_radius=0, wrap="word",
            state="disabled", scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=ACCENT
        )
        self.text_box.pack(fill="both", expand=True, padx=6, pady=(0, 6))

    def set_status(self, text, color):
        self.status_label.configure(text=f"● {text}", text_color=color)

    def clear(self):
        self.text_box.configure(state="normal")
        self.text_box.delete("1.0", "end")
        self.text_box.configure(state="disabled")
        self.set_status("STANDBY", TEXT_DIM)

    def append(self, text):
        self.text_box.configure(state="normal")
        self.text_box.insert("end", text)
        self.text_box.see("end")
        self.text_box.configure(state="disabled")


# ── Main Application ──────────────────────────────────────────────────────────
class CounselApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("THE COUNSEL  ◆  Multi-Agent Decision Engine")
        self.geometry("1400x900")
        self.minsize(1100, 720)
        self.configure(fg_color=BG_DEEP)

        self.client = MockClient() if USE_MOCK else BackboardClient()
        self._running = False
        self._log_data = []

        self._build_ui()

        if USE_MOCK:
            self._set_status(
                "MOCK MODE — Add your API key and agent IDs to main.py to use real AI"
            )

    def _build_ui(self):
        # Top bar
        topbar = ctk.CTkFrame(self, fg_color=BG_PANEL, height=56, corner_radius=0)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        ctk.CTkLabel(topbar, text="  ◈  THE COUNSEL",
                     font=("Segoe UI", 16, "bold"),
                     text_color=ACCENT).pack(side="left", padx=16)
        ctk.CTkLabel(topbar, text="Multi-Agent C-Suite Decision Engine",
                     font=("Segoe UI", 11),
                     text_color=TEXT_DIM).pack(side="left")

        self.session_label = ctk.CTkLabel(topbar, text="SESSION: --",
                                           font=("Courier", 10), text_color=TEXT_DIM)
        self.session_label.pack(side="right", padx=16)

        # Input
        input_frame = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=8)
        input_frame.pack(fill="x", padx=16, pady=(12, 8))

        ctk.CTkLabel(input_frame, text="QUERY INPUT",
                     font=("Segoe UI", 10, "bold"),
                     text_color=TEXT_DIM).pack(anchor="w", padx=14, pady=(10, 4))

        input_row = ctk.CTkFrame(input_frame, fg_color="transparent")
        input_row.pack(fill="x", padx=14, pady=(0, 12))

        self.prompt_box = ctk.CTkTextbox(
            input_row, height=72, font=("Segoe UI", 12),
            fg_color=BG_INPUT, text_color=TEXT_MAIN,
            border_color=BORDER, border_width=1, corner_radius=6, wrap="word"
        )
        self.prompt_box.pack(side="left", fill="x", expand=True, padx=(0, 12))
        self.prompt_box.insert("1.0",
            "We are considering a major infrastructure overhaul. "
            "Should we migrate our entire data pipeline to a microservices architecture this quarter?"
        )
        self.prompt_box.bind("<Control-Return>", lambda e: self._convene())

        self.convene_btn = ctk.CTkButton(
            input_row, text="⬡  CONVENE\n    COUNSEL",
            font=("Segoe UI", 13, "bold"),
            fg_color=ACCENT, hover_color="#3949AB",
            text_color="white", corner_radius=6,
            width=140, height=72, command=self._convene
        )
        self.convene_btn.pack(side="right")

        # Agent panels
        agents_frame = ctk.CTkFrame(self, fg_color="transparent")
        agents_frame.pack(fill="both", expand=True, padx=16, pady=4)
        agents_frame.columnconfigure((0, 1, 2), weight=1)
        agents_frame.rowconfigure(0, weight=1)

        self.gemini_card = AgentCard(
            agents_frame,
            title="AGENT A  ·  THE TECHNICIAN",
            subtitle="Gemini Flash  ·  Speed & Raw Data",
            color=GEMINI_C
        )
        self.gemini_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self.claude_card = AgentCard(
            agents_frame,
            title="AGENT B  ·  THE AUDITOR",
            subtitle="Claude Sonnet  ·  Flaw Detection & Safety",
            color=CLAUDE_C
        )
        self.claude_card.grid(row=0, column=1, sticky="nsew", padx=3)

        self.gpt_card = AgentCard(
            agents_frame,
            title="AGENT C  ·  THE CHAIRMAN",
            subtitle="GPT-4o  ·  Synthesis & Final Ruling",
            color=GPT_C
        )
        self.gpt_card.grid(row=0, column=2, sticky="nsew", padx=(6, 0))

        # Consensus
        consensus_frame = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=8,
                                        border_width=1, border_color=BORDER)
        consensus_frame.pack(fill="x", padx=16, pady=(8, 12))

        consensus_header = ctk.CTkFrame(consensus_frame, fg_color=BG_PANEL,
                                         corner_radius=0, height=40)
        consensus_header.pack(fill="x")
        consensus_header.pack_propagate(False)

        ctk.CTkLabel(consensus_header, text="  ◆  FINAL CONSENSUS",
                     font=("Segoe UI", 11, "bold"),
                     text_color=CONSENSUS).pack(side="left", pady=10, padx=8)

        self.consensus_status = ctk.CTkLabel(
            consensus_header, text="AWAITING DELIBERATION",
            font=("Courier", 10), text_color=TEXT_DIM
        )
        self.consensus_status.pack(side="left", padx=8)

        ctk.CTkButton(
            consensus_header, text="⬇  SAVE LOG",
            font=("Segoe UI", 10, "bold"),
            fg_color="transparent", hover_color=BORDER,
            text_color=TEXT_DIM, border_color=BORDER, border_width=1,
            corner_radius=4, width=100, height=26,
            command=self._save_log
        ).pack(side="right", padx=12, pady=7)

        self.consensus_box = ctk.CTkTextbox(
            consensus_frame, height=110, font=("Segoe UI", 12),
            fg_color=BG_INPUT, text_color=CONSENSUS,
            corner_radius=0, wrap="word", state="disabled",
            scrollbar_button_color=BORDER
        )
        self.consensus_box.pack(fill="x", padx=6, pady=(0, 6))

        # Status bar
        statusbar = ctk.CTkFrame(self, fg_color=BG_PANEL, height=28, corner_radius=0)
        statusbar.pack(fill="x", side="bottom")
        statusbar.pack_propagate(False)

        self.status_bar = ctk.CTkLabel(
            statusbar,
            text="Ready. Press Ctrl+Enter or click CONVENE COUNSEL to begin.",
            font=("Segoe UI", 10), text_color=TEXT_DIM, anchor="w"
        )
        self.status_bar.pack(side="left", padx=14)

    # ── Thread-safe UI helpers ────────────────────────────────────────────────
    # ALL widget updates must go through self.after(0, fn) when called from
    # a background thread — Tkinter is single-threaded and will segfault otherwise.

    def _ui(self, fn):
        """Schedule fn() to run on the main thread."""
        self.after(0, fn)

    def _set_status(self, text):
        self._ui(lambda: self.status_bar.configure(text=text))

    def _card_append(self, card, text):
        self._ui(lambda: card.append(text))

    def _card_status(self, card, text, color):
        self._ui(lambda: card.set_status(text, color))

    def _consensus_append(self, text):
        def _do():
            self.consensus_box.configure(state="normal")
            self.consensus_box.insert("end", text)
            self.consensus_box.see("end")
            self.consensus_box.configure(state="disabled")
        self._ui(_do)

    def _set_verdict(self, text, color):
        self._ui(lambda: self.consensus_status.configure(text=text, text_color=color))

    def _session_done(self):
        self._ui(lambda: self.convene_btn.configure(
            state="normal", text="⬡  CONVENE\n    COUNSEL"
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
        self.convene_btn.configure(state="disabled", text="⏳ IN SESSION...")
        self._log_data = []
        self.session_label.configure(
            text=f"SESSION: {datetime.now().strftime('SES-%H%M%S')}"
        )

        for card in [self.gemini_card, self.claude_card, self.gpt_card]:
            card.clear()
        self.consensus_box.configure(state="normal")
        self.consensus_box.delete("1.0", "end")
        self.consensus_box.configure(state="disabled")
        self.consensus_status.configure(
            text="DELIBERATION IN PROGRESS...", text_color=TEXT_DIM
        )

        threading.Thread(target=self._run_session, args=(prompt,), daemon=True).start()

    def _run_session(self, prompt: str):
        try:
            # ── Phase 1: The Technician ───────────────────────────────────────
            self._set_status("Phase 1/3  ·  The Technician analyzing...")
            self._card_status(self.gemini_card, "PROCESSING", GEMINI_C)

            thread_1 = self.client.create_thread(TECHNICIAN_ID)
            gemini_output = []

            def on_gemini(t):
                gemini_output.append(t)
                self._card_append(self.gemini_card, t)

            self.client.send_message_stream(
                thread_id=thread_1,
                content=prompt,
                llm_provider=TECHNICIAN_PROVIDER,
                model_name=TECHNICIAN_MODEL,
                memory="Auto",
                on_chunk=on_gemini
            )
            self._card_status(self.gemini_card, "COMPLETE", GEMINI_C)
            gemini_text = "".join(gemini_output)
            self._log_data.append(("THE TECHNICIAN (Gemini Flash)", gemini_text))

            # ── Phase 2: The Auditor ──────────────────────────────────────────
            self._set_status("Phase 2/3  ·  The Auditor reviewing Technician's output...")
            self._card_status(self.claude_card, "AUDITING", CLAUDE_C)

            thread_2 = self.client.create_thread(AUDITOR_ID)
            audit_prompt = (
                f"The following analysis was produced in response to this query:\n"
                f"QUERY: {prompt}\n\n"
                f"TECHNICIAN'S ANALYSIS:\n{gemini_text}\n\n"
                f"Audit the above for risks, blind spots, unstated assumptions, "
                f"and safety concerns. Be adversarial and thorough."
            )
            claude_output = []

            def on_claude(t):
                claude_output.append(t)
                self._card_append(self.claude_card, t)

            self.client.send_message_stream(
                thread_id=thread_2,
                content=audit_prompt,
                llm_provider=AUDITOR_PROVIDER,
                model_name=AUDITOR_MODEL,
                memory="Auto",
                on_chunk=on_claude
            )
            self._card_status(self.claude_card, "COMPLETE", CLAUDE_C)
            claude_text = "".join(claude_output)
            self._log_data.append(("THE AUDITOR (Claude Sonnet)", claude_text))

            # ── Phase 3: The Chairman ─────────────────────────────────────────
            self._set_status("Phase 3/3  ·  The Chairman deliberating final consensus...")
            self._card_status(self.gpt_card, "DELIBERATING", GPT_C)

            thread_3 = self.client.create_thread(CHAIRMAN_ID)
            synthesis_prompt = (
                f"ORIGINAL QUERY: {prompt}\n\n"
                f"TECHNICIAN'S ANALYSIS:\n{gemini_text}\n\n"
                f"AUDITOR'S CRITIQUE:\n{claude_text}\n\n"
                f"Synthesize both positions and issue your final ruling. "
                f"IMPORTANT: You MUST begin your response with exactly 'Consensus Reached:' "
                f"if the two agents can be reconciled, or 'Deadlock:' only if their positions "
                f"are truly irreconcilable. In most cases a consensus is possible — deadlock "
                f"should be rare. No other opening word or phrase is acceptable."
            )
            gpt_output = []

            def on_gpt(t):
                gpt_output.append(t)
                self._card_append(self.gpt_card, t)
                self._consensus_append(t)

            self.client.send_message_stream(
                thread_id=thread_3,
                content=synthesis_prompt,
                llm_provider=CHAIRMAN_PROVIDER,
                model_name=CHAIRMAN_MODEL,
                memory="Auto",
                on_chunk=on_gpt
            )
            self._card_status(self.gpt_card, "COMPLETE", GPT_C)
            gpt_text = "".join(gpt_output)
            self._log_data.append(("THE CHAIRMAN (GPT-4o)", gpt_text))

            # ── Verdict — case-insensitive check ─────────────────────────────
            gpt_lower = gpt_text.strip().lower()
            if gpt_lower.startswith("consensus reached"):
                self._set_verdict("✓ CONSENSUS REACHED", "#A5D6A7")
            elif gpt_lower.startswith("deadlock"):
                self._set_verdict("⚡ DEADLOCK DECLARED", "#EF9A9A")
            else:
                self._set_verdict("RULING ISSUED", CONSENSUS)

            self._set_status("✓ Session complete. The Counsel has spoken.")

        except requests.HTTPError as e:
            self._set_status(
                f"API error: {e.response.status_code} — {e.response.text[:120]}"
            )
        except Exception as e:
            self._set_status(f"Session error: {e}")
        finally:
            self._running = False
            self._session_done()

    def _save_log(self):
        if not self._log_data:
            self._set_status("No session data to save.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"counsel_log_{timestamp}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write("THE COUNSEL — SESSION LOG\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 70 + "\n\n")
            for agent, content in self._log_data:
                f.write(f"[ {agent} ]\n")
                f.write("-" * 50 + "\n")
                f.write(content + "\n\n")
        self._set_status(f"✓ Log saved → {filename}")


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = CounselApp()
    app.mainloop()
