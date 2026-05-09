from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from shared.transcript_utils import split_combined_transcript
from enrichment.config import (
    AUDIO_SOURCE_CANDIDATES,
    COMBINED_FALLBACK_DIR,
    COMBINED_TRANSCRIPT_CANDIDATES,
    ENRICHED_TRANSCRIPT_SOURCE_CANDIDATES,
    MANUAL_INPUT_SOURCE_CANDIDATES,
    MAX_BATCH_SIZE,
    STRUCTURED_TRANSCRIPT_SOURCE_CANDIDATES,
    SUPPORTED_AUDIO_EXTENSIONS,
    TRANSCRIPT_TEXT_SOURCE_CANDIDATES,
)
from shared.json_utils import read_json, write_text_atomic


@dataclass(frozen=True)
class Phase3Input:
    call_id: str
    audio_path: Path | None
    transcript_path: Path
    transcript_metadata_path: Path | None
    transcript_format: str
    transcript_source: str
    transcript_priority: int
    reviewed: bool
    enrichment_level: str
    pipeline_stage: str


def discover_inputs() -> tuple[list[Phase3Input], list[str]]:
    audio_lookup = _discover_audio_files()
    transcript_lookup = _discover_transcripts()
    discovered: list[Phase3Input] = []
    warnings: list[str] = []

    for call_id in sorted(transcript_lookup.keys())[:MAX_BATCH_SIZE]:
        transcript_candidate = transcript_lookup[call_id]
        metadata_candidate = transcript_candidate.transcript_path.with_suffix(".metadata.json")
        transcript_metadata_path = metadata_candidate if metadata_candidate.exists() else transcript_candidate.transcript_metadata_path
        discovered.append(
            Phase3Input(
                call_id=call_id,
                audio_path=audio_lookup.get(call_id),
                transcript_path=transcript_candidate.transcript_path,
                transcript_metadata_path=transcript_metadata_path,
                transcript_format=transcript_candidate.transcript_format,
                transcript_source=transcript_candidate.transcript_source,
                transcript_priority=transcript_candidate.priority,
                reviewed=transcript_candidate.reviewed,
                enrichment_level=transcript_candidate.enrichment_level,
                pipeline_stage=transcript_candidate.pipeline_stage,
            )
        )

    transcript_only = sorted(call_id for call_id, item in transcript_lookup.items() if audio_lookup.get(call_id) is None)
    for call_id in transcript_only:
        warnings.append(f"Transcript exists without audio pair: {call_id}. Transcript enrichment will continue without acoustic analysis.")

    audio_only = sorted(set(audio_lookup.keys()) - set(transcript_lookup.keys()))
    for call_id in audio_only:
        warnings.append(f"Audio exists without a preferred transcript source: {call_id}")

    return discovered, warnings


def _discover_audio_files() -> dict[str, Path]:
    audio_paths: dict[str, Path] = {}
    for candidate_dir in AUDIO_SOURCE_CANDIDATES:
        if not candidate_dir.exists():
            continue
        for path in sorted(candidate_dir.rglob("*")):
            if path.is_file() and path.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS:
                audio_paths.setdefault(_normalize_call_id(path.stem), path)
    return {key: audio_paths[key] for key in sorted(audio_paths.keys())}


@dataclass(frozen=True)
class TranscriptCandidate:
    call_id: str
    transcript_path: Path
    transcript_metadata_path: Path | None
    transcript_format: str
    transcript_source: str
    priority: int
    reviewed: bool
    enrichment_level: str
    pipeline_stage: str


def _discover_transcripts() -> dict[str, TranscriptCandidate]:
    transcripts: dict[str, TranscriptCandidate] = {}

    for candidate_dir in MANUAL_INPUT_SOURCE_CANDIDATES:
        if not candidate_dir.exists():
            continue
        for path in sorted(candidate_dir.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".json", ".txt", ".md"}:
                continue
            call_id = _extract_call_id_from_path(path)
            if not call_id:
                continue
            transcript_format, enrichment_level, reviewed = _classify_manual_file(candidate_dir, path)
            _upsert_candidate(
                transcripts,
                TranscriptCandidate(
                    call_id=call_id,
                    transcript_path=path,
                    transcript_metadata_path=path.with_suffix(".metadata.json") if path.suffix.lower() in {".txt", ".md"} and path.with_suffix(".metadata.json").exists() else None,
                    transcript_format=transcript_format,
                    transcript_source=str(candidate_dir.name),
                    priority=_manual_priority(candidate_dir.name, transcript_format),
                    reviewed=reviewed,
                    enrichment_level=enrichment_level,
                    pipeline_stage="phase_3",
                ),
            )

    for candidate_dir in ENRICHED_TRANSCRIPT_SOURCE_CANDIDATES:
        if not candidate_dir.exists():
            continue
        for path in sorted(candidate_dir.glob("CALL_*.json")):
            payload = read_json(path, default={}) or {}
            if "conversation_intelligence" not in payload:
                continue
            _upsert_candidate(
                transcripts,
                TranscriptCandidate(
                    call_id=_normalize_call_id(path.stem),
                    transcript_path=path,
                    transcript_metadata_path=None,
                    transcript_format="enriched_json",
                    transcript_source="phase_3_enriched_json",
                    priority=3,
                    reviewed=bool((payload.get("source_tracking", {}) or {}).get("reviewed")),
                    enrichment_level=str((payload.get("source_tracking", {}) or {}).get("enrichment_level", "high")),
                    pipeline_stage=str((payload.get("source_tracking", {}) or {}).get("pipeline_stage", "phase_3")),
                ),
            )

    for candidate_dir in STRUCTURED_TRANSCRIPT_SOURCE_CANDIDATES:
        if not candidate_dir.exists():
            continue
        for path in sorted(candidate_dir.glob("CALL_*.json")):
            _upsert_candidate(
                transcripts,
                TranscriptCandidate(
                    call_id=_normalize_call_id(path.stem),
                    transcript_path=path,
                    transcript_metadata_path=None,
                    transcript_format="structured_json",
                    transcript_source="phase_2_structured_json",
                    priority=4,
                    reviewed=False,
                    enrichment_level="medium",
                    pipeline_stage="phase_2",
                ),
            )

    for candidate_dir in TRANSCRIPT_TEXT_SOURCE_CANDIDATES:
        if not candidate_dir.exists():
            continue
        for path in sorted(candidate_dir.rglob("*.txt")):
            stem = path.stem.replace("_summary", "")
            if not stem.lower().startswith("call_"):
                continue
            source = "normalized_txt" if "outputs" in str(path.parent).lower() else "raw_txt"
            priority = 5 if source == "normalized_txt" else 6
            _upsert_candidate(
                transcripts,
                TranscriptCandidate(
                    call_id=_normalize_call_id(stem),
                    transcript_path=path,
                    transcript_metadata_path=path.with_suffix(".metadata.json") if path.with_suffix(".metadata.json").exists() else None,
                    transcript_format=source,
                    transcript_source=str(path.parent.name),
                    priority=priority,
                    reviewed=False,
                    enrichment_level="medium" if source == "normalized_txt" else "low",
                    pipeline_stage="phase_2",
                ),
            )

    for combined_file in COMBINED_TRANSCRIPT_CANDIDATES:
        if not combined_file.exists():
            continue
        content = combined_file.read_text(encoding="utf-8")
        for block in split_combined_transcript(content):
            fallback_path = COMBINED_FALLBACK_DIR / f"{block.call_id}.txt"
            if not fallback_path.exists():
                write_text_atomic(fallback_path, block.block_text, encoding="utf-8")
            _upsert_candidate(
                transcripts,
                TranscriptCandidate(
                    call_id=block.call_id,
                    transcript_path=fallback_path,
                    transcript_metadata_path=None,
                    transcript_format="combined_fallback",
                    transcript_source="combined_transcript_fallback",
                    priority=7,
                    reviewed=False,
                    enrichment_level="low",
                    pipeline_stage="phase_2",
                ),
            )
    return transcripts


def _upsert_candidate(store: dict[str, TranscriptCandidate], candidate: TranscriptCandidate) -> None:
    current = store.get(candidate.call_id)
    if current is None or candidate.priority < current.priority:
        store[candidate.call_id] = candidate


def _normalize_call_id(raw_call_id: str) -> str:
    digits = "".join(character for character in raw_call_id if character.isdigit())
    if digits:
        return f"CALL_{digits.zfill(4)}"
    return raw_call_id.strip().upper()


def _extract_call_id_from_path(path: Path) -> str | None:
    normalized = _normalize_call_id(path.stem)
    if normalized.startswith("CALL_"):
        return normalized
    for part in path.parts:
        candidate = _normalize_call_id(part)
        if candidate.startswith("CALL_"):
            return candidate
    return None


def _classify_manual_file(candidate_dir: Path, path: Path) -> tuple[str, str, bool]:
    directory_name = candidate_dir.name.lower()
    suffix = path.suffix.lower()
    if suffix == ".json":
        payload = read_json(path, default={}) or {}
        source_tracking = payload.get("source_tracking", {}) or {}
        reviewed = bool(source_tracking.get("reviewed", directory_name in {"manual_reviews", "corrected_calls"}))
        enrichment_level = str(source_tracking.get("enrichment_level", "high" if reviewed else "medium"))
        if payload.get("conversation_intelligence"):
            return "manual_enriched_json", enrichment_level, reviewed
        return "manual_structured_json", enrichment_level, reviewed
    reviewed = directory_name in {"manual_reviews", "corrected_calls"}
    if suffix == ".md":
        return "manual_reviewed_markdown" if reviewed else "manual_markdown", "high" if reviewed else "medium", reviewed
    return "manual_reviewed_txt" if reviewed else "manual_txt", "high" if reviewed else "medium", reviewed


def _manual_priority(directory_name: str, transcript_format: str) -> int:
    normalized = directory_name.lower()
    if normalized == "manual_reviews":
        return 1
    if normalized == "corrected_calls":
        return 2
    if transcript_format == "manual_enriched_json":
        return 2
    if transcript_format in {"manual_reviewed_txt", "manual_reviewed_markdown"}:
        return 2
    if normalized == "enriched_json":
        return 2
    return 3
