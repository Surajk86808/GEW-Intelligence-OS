from __future__ import annotations

import re


def normalize_phone_number(value: object) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    if not text or text.lower() == "nan":
        return ""

    if "." in text:
        text = text.split(".")[0]

    digits = re.sub(r"\D", "", text)
    if not digits:
        return ""
    if len(digits) >= 10:
        return digits[-10:]
    return digits

