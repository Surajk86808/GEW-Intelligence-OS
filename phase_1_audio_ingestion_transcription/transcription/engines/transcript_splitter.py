from __future__ import annotations

import re
from dataclasses import dataclass

CALL_HEADER_PATTERN = re.compile(r"^(CALL[_\-\s]?\d+)(?:\.\w+)?\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class TranscriptBlock:
    call_id: str
    raw_header: str
    block_text: str


def split_combined_transcript(content: str) -> list[TranscriptBlock]:
    lines = content.splitlines()
    blocks: list[TranscriptBlock] = []
    current_call_id = ""
    current_header = ""
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        match = CALL_HEADER_PATTERN.match(stripped)
        if match:
            if current_call_id and current_lines:
                blocks.append(
                    TranscriptBlock(
                        call_id=_normalize_call_id(current_call_id),
                        raw_header=current_header,
                        block_text="\n".join(current_lines).strip(),
                    )
                )
            current_call_id = match.group(1)
            current_header = stripped
            current_lines = [stripped]
            continue

        if current_call_id:
            current_lines.append(line)

    if current_call_id and current_lines:
        blocks.append(
            TranscriptBlock(
                call_id=_normalize_call_id(current_call_id),
                raw_header=current_header,
                block_text="\n".join(current_lines).strip(),
            )
        )

    return blocks


def _normalize_call_id(raw_call_id: str) -> str:
    digits = re.sub(r"\D", "", raw_call_id)
    if not digits:
        return raw_call_id.strip().upper()
    return f"CALL_{digits.zfill(4)}"
