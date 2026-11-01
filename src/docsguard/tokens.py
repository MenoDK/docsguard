"""Token estimation.

An estimate, not a count: English prose averages roughly four characters per token, code and other
languages drift from that. It is good enough to *budget* (is this file 800 tokens or 8000?), which is
all the instruction budget needs, and it keeps the tool dependency-free. Never use it for billing.
"""

from __future__ import annotations

import math

CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    return math.ceil(len(text) / CHARS_PER_TOKEN)
