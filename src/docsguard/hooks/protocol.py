"""The Claude Code hook wire format, in one place.

A ``PreToolUse`` hook receives a JSON payload on stdin and may answer with a JSON decision on stdout.
Anything the hook cannot understand is allowed: a guard that blocks on its own parsing failures gets
switched off by the first person it annoys, which is worse than the accident it was written for.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, TextIO


@dataclass(frozen=True, slots=True)
class Decision:
    rule: str
    reason: str


def read_payload(stream: TextIO) -> dict[str, Any] | None:
    try:
        data = json.load(stream)
    except (ValueError, OSError):
        return None
    return data if isinstance(data, dict) else None


def tool_input(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("tool_input")
    return value if isinstance(value, dict) else {}


def emit_deny(stream: TextIO, decision: Decision) -> None:
    message = f"[docsguard:{decision.rule}] {decision.reason}"
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": message,
            }
        },
        stream,
    )
    stream.write("\n")
