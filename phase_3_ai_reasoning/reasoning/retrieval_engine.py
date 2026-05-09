from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from reasoning.config import CHUNK_INDEX_DIR, MAX_RETRIEVAL_CHUNKS, TRANSCRIPT_CHUNK_LINE_COUNT
from shared.json_utils import write_json

TIMESTAMP_PATTERN = re.compile(r"^\[(\d{2}:\d{2})\]\s+(.*)$")


@dataclass
class TranscriptChunk:
    chunk_id: str
    start_timestamp: str
    end_timestamp: str
    text: str
    keywords: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp,
            "text": self.text,
            "keywords": self.keywords,
        }


class RetrievalEngine:
    def build_chunk_index(self, call_id: str, transcript_text: str) -> list[TranscriptChunk]:
        chunks: list[TranscriptChunk] = []
        lines = [line.strip() for line in transcript_text.splitlines() if line.strip()]
        bucket: list[tuple[str, str]] = []
        for line in lines:
            match = TIMESTAMP_PATTERN.match(line)
            timestamp = match.group(1) if match else ""
            text = match.group(2) if match else line
            bucket.append((timestamp, text))
            if len(bucket) >= TRANSCRIPT_CHUNK_LINE_COUNT:
                chunks.append(self._build_chunk(call_id, len(chunks), bucket))
                bucket = []
        if bucket:
            chunks.append(self._build_chunk(call_id, len(chunks), bucket))

        write_json(CHUNK_INDEX_DIR / f"{call_id}.json", [chunk.to_dict() for chunk in chunks])
        return chunks

    def retrieve(self, call_id: str, transcript_text: str, search_terms: list[str]) -> list[dict[str, Any]]:
        chunks = self.build_chunk_index(call_id, transcript_text)
        scored: list[tuple[int, TranscriptChunk]] = []
        lowered_terms = [term.lower() for term in search_terms if term.strip()]
        for chunk in chunks:
            haystack = f"{chunk.text} {' '.join(chunk.keywords)}".lower()
            score = sum(1 for term in lowered_terms if term in haystack)
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [chunk.to_dict() for _, chunk in scored[:MAX_RETRIEVAL_CHUNKS]]

    def _build_chunk(self, call_id: str, index: int, bucket: list[tuple[str, str]]) -> TranscriptChunk:
        timestamps = [timestamp for timestamp, _ in bucket if timestamp]
        texts = [text for _, text in bucket]
        keywords = _extract_keywords(" ".join(texts))
        return TranscriptChunk(
            chunk_id=f"{call_id}_chunk_{index + 1:03d}",
            start_timestamp=timestamps[0] if timestamps else "",
            end_timestamp=timestamps[-1] if timestamps else "",
            text="\n".join(texts),
            keywords=keywords,
        )


def _extract_keywords(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z]{4,}", text.lower())
    stop_words = {"this", "that", "with", "have", "from", "they", "your", "about", "there", "would", "could"}
    keywords = []
    for word in words:
        if word in stop_words:
            continue
        if word not in keywords:
            keywords.append(word)
    return keywords[:20]

