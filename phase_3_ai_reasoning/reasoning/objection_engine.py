from __future__ import annotations

import re
from typing import Any


class ObjectionEngine:
    def validate(self, objections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        validated: list[dict[str, Any]] = []
        for objection in objections:
            if not objection.get("timestamp") or not objection.get("evidence"):
                continue
            objection["confidence"] = _clamp(objection.get("confidence", 0.0))
            validated.append(objection)
        return validated

    def detect_rule_based_signals(self, transcript_text: str) -> list[str]:
        lower = transcript_text.lower()
        flags = []
        rule_map = {
            "pricing resistance": [r"\bexpensive\b", r"\btoo high\b", r"\bprice\b", r"\bbudget\b"],
            "timing issue": [r"\blater\b", r"\bnext month\b", r"\bnot now\b", r"\bafter\b"],
            "trust concern": [r"\bnot sure\b", r"\btrust\b", r"\bscam\b", r"\bproof\b"],
            "competitor present": [r"\balready using\b", r"\bcurrent provider\b", r"\bcompetitor\b"],
        }
        for label, patterns in rule_map.items():
            if any(re.search(pattern, lower) for pattern in patterns):
                flags.append(label)
        return flags


def _clamp(value: Any) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 2)
    except Exception:
        return 0.0

