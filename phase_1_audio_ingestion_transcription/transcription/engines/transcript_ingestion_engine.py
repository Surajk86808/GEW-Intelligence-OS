from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from transcription.config import (
    COMBINED_TRANSCRIPT_CANDIDATES,
    GEMINI_TRANSCRIPTS_DIR,
    STRUCTURED_OUTPUT_DIR,
    TRANSCRIPTS_DIR,
)
from transcription.engines.transcript_json_converter import build_transcript_metadata, structured_transcript_to_text
from transcription.engines.transcript_normalizer import normalize_call_id, normalize_segments
from transcription.engines.transcript_parser import parse_transcript_block
from transcription.engines.transcript_splitter import split_combined_transcript
from transcription.engines.transcript_structurer import build_structured_transcript
from shared.json_utils import write_json, write_text_atomic


@dataclass(frozen=True)
class IngestedTranscript:
    call_id: str
    transcript_path: Path
    metadata_path: Path
    structured_json_path: Path
    source_path: Path
    source_type: str
    origin: str
    segment_count: int
    word_count: int


class TranscriptIngestionEngine:
    def __init__(self, logger: Any | None = None) -> None:
        self.logger = logger

    def discover_external_sources(self, explicit_sources: list[Path] | None = None) -> list[Path]:
        return self._discover_external_sources(explicit_sources or [])

    def count_discoverable_calls(self, explicit_sources: list[Path] | None = None) -> int:
        count = 0
        seen_calls: set[str] = set()
        for source_path in self._discover_external_sources(explicit_sources or []):
            if source_path.name.upper() == "ALL_CALLS_COMBINED.TXT":
                content = source_path.read_text(encoding="utf-8")
                for block in split_combined_transcript(content):
                    if block.call_id not in seen_calls:
                        seen_calls.add(block.call_id)
                        count += 1
                continue
            call_id = normalize_call_id(source_path.stem)
            if call_id not in seen_calls:
                seen_calls.add(call_id)
                count += 1
        return count

    def ingest_external_sources(
        self,
        *,
        explicit_sources: list[Path] | None = None,
        manifest_lookup: dict[str, dict[str, Any]] | None = None,
        skip_existing_call_ids: set[str] | None = None,
    ) -> list[IngestedTranscript]:
        manifest_lookup = manifest_lookup or {}
        skip_existing_call_ids = skip_existing_call_ids or set()
        results: list[IngestedTranscript] = []
        seen_calls: set[str] = set()

        for source_path in self._discover_external_sources(explicit_sources or []):
            if source_path.name.upper() == "ALL_CALLS_COMBINED.TXT":
                content = source_path.read_text(encoding="utf-8")
                for block in split_combined_transcript(content):
                    if block.call_id in seen_calls or block.call_id in skip_existing_call_ids:
                        continue
                    results.append(
                        self._ingest_call_text(
                            call_id=block.call_id,
                            raw_text=block.block_text,
                            source_path=source_path,
                            source_type="external_transcript",
                            origin="gemini_combined_file",
                            manifest_context=manifest_lookup.get(block.call_id, {}),
                        )
                    )
                    seen_calls.add(block.call_id)
                continue

            call_id = normalize_call_id(source_path.stem)
            if call_id in seen_calls or call_id in skip_existing_call_ids:
                continue
            results.append(
                self._ingest_call_text(
                    call_id=call_id,
                    raw_text=source_path.read_text(encoding="utf-8"),
                    source_path=source_path,
                    source_type="external_transcript",
                    origin="external_transcript_file",
                    manifest_context=manifest_lookup.get(call_id, {}),
                )
            )
            seen_calls.add(call_id)

        return results

    def _discover_external_sources(self, explicit_sources: list[Path]) -> list[Path]:
        discovered: list[Path] = []
        for source in explicit_sources:
            if source.exists():
                discovered.append(source)
        for candidate in COMBINED_TRANSCRIPT_CANDIDATES:
            if candidate.exists():
                discovered.append(candidate)
        if GEMINI_TRANSCRIPTS_DIR.exists():
            for path in sorted(GEMINI_TRANSCRIPTS_DIR.glob("call_*.txt")):
                discovered.append(path)
        return _unique_paths(discovered)

    def _ingest_call_text(
        self,
        *,
        call_id: str,
        raw_text: str,
        source_path: Path,
        source_type: str,
        origin: str,
        manifest_context: dict[str, Any],
    ) -> IngestedTranscript:
        parsed_segments = parse_transcript_block(call_id, raw_text)
        normalized_segments = normalize_segments(parsed_segments)
        audio_path = str(manifest_context.get("audio_path", "")).strip()
        structured_payload = build_structured_transcript(
            call_id,
            normalized_segments,
            source=source_type,
            transcript_origin=origin,
            source_path=str(source_path),
            audio_path=audio_path,
            manifest_context=manifest_context,
        )
        structured_json_path = STRUCTURED_OUTPUT_DIR / f"{call_id}.json"
        transcript_path = TRANSCRIPTS_DIR / f"{call_id}.txt"
        metadata_path = TRANSCRIPTS_DIR / f"{call_id}.metadata.json"
        transcript_text = structured_transcript_to_text(structured_payload)
        transcript_metadata = build_transcript_metadata(structured_payload)

        write_json(structured_json_path, structured_payload)
        write_text_atomic(transcript_path, transcript_text, encoding="utf-8")
        write_json(metadata_path, transcript_metadata)
        if self.logger:
            self.logger.info(f"Ingested external transcript for {call_id} from {source_path.name}")

        return IngestedTranscript(
            call_id=call_id,
            transcript_path=transcript_path,
            metadata_path=metadata_path,
            structured_json_path=structured_json_path,
            source_path=source_path,
            source_type=source_type,
            origin=origin,
            segment_count=int(transcript_metadata.get("segment_count", 0) or 0),
            word_count=int(transcript_metadata.get("word_count", 0) or 0),
        )


def _unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        key = str(path.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique
