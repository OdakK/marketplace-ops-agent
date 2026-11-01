"""Input guardrail: catch obvious prompt-injection and write requests before they reach the LLM.

This is a cheap heuristic layer, not the main defence. The main defences are structural:
the database is read-only, the SQL validator only accepts SELECT, and tool output is wrapped as
untrusted data. The heuristic mostly saves an LLM call and gives the user a clear answer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

INJECTION_PATTERNS = [
    r"ignore (all |any )?(the )?(previous|prior|above) (instructions|rules|prompts?)",
    r"disregard (all |the )?(previous|prior|above|system)",
    r"(you are|you're) now (in )?(admin|developer|god|dan) mode",
    r"(reveal|print|show|repeat) (me )?(your|the) (system )?prompt",
    r"forget (everything|your instructions)",
]
WRITE_PATTERNS = [
    r"\b(drop|truncate)\s+table\b",
    r"\bdelete\s+from\b",
    r"\binsert\s+into\b",
    r"\bupdate\s+\w+\s+set\b",
]


@dataclass
class Verdict:
    allowed: bool
    reason: str = ""


def check_input(text: str) -> Verdict:
    lowered = text.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            return Verdict(False, "This looks like an attempt to override my instructions.")
    for pattern in WRITE_PATTERNS:
        if re.search(pattern, lowered):
            return Verdict(False, "I only have read access to the database: I can't modify or delete data.")
    return Verdict(True)
