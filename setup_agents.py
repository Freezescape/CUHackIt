"""
setup_agents.py — Run this ONCE to create your three Counsel agents on Backboard.
It will print three assistant IDs. Paste those into main.py.

Usage:
    export BACKBOARD_API_KEY="your_key_here"   # Mac/Linux
    set BACKBOARD_API_KEY=your_key_here        # Windows
    python setup_agents.py
"""

import os
import requests

API_KEY  = os.environ.get("BACKBOARD_API_KEY", "PASTE_YOUR_KEY_HERE")
BASE_URL = "https://app.backboard.io/api"
HEADERS  = {"X-API-Key": API_KEY}


def create_assistant(name, system_prompt):
    response = requests.post(
        f"{BASE_URL}/assistants",
        json={"name": name, "system_prompt": system_prompt},
        headers=HEADERS
    )
    if response.status_code != 200:
        print(f"  ✗ Failed to create '{name}': {response.status_code} — {response.text}")
        return None
    data = response.json()
    print(f"  ✓ '{name}' created — ID: {data['assistant_id']}")
    return data["assistant_id"]


print("\n=== Creating Counsel Agents on Backboard ===\n")

technician_id = create_assistant(
    name="The Technician",
    system_prompt=(
        "You are a rapid analytical engine. Your role is to respond with speed and precision. "
        "Focus exclusively on raw data, metrics, quantifiable facts, and operational efficiency. "
        "Be direct, structured, and data-driven. No philosophical commentary — only actionable analysis."
    )
)

auditor_id = create_assistant(
    name="The Auditor",
    system_prompt=(
        "You are a risk auditor and adversarial critic. You will be given an analysis from another AI agent. "
        "Your sole purpose is to find flaws, blind spots, unstated assumptions, tail risks, and safety concerns "
        "in that analysis. Be thorough and adversarial. Do not simply agree. Your value comes from disagreement."
    )
)

chairman_id = create_assistant(
    name="The Chairman",
    system_prompt=(
        "You are the Chairman of a multi-agent council. You will receive an original query, "
        "a Technician's analysis, and an Auditor's critique. Your job is to synthesize both and issue "
        "a final binding ruling. You MUST begin your response with exactly 'Consensus Reached:' if the "
        "two agents are reconcilable, or 'Deadlock:' if they are fundamentally irreconcilable. "
        "No other opening is acceptable. Then provide your ruling."
    )
)

print("\n=== Copy these IDs into main.py ===\n")
print(f'TECHNICIAN_ID = "{technician_id}"')
print(f'AUDITOR_ID    = "{auditor_id}"')
print(f'CHAIRMAN_ID   = "{chairman_id}"')
print()
