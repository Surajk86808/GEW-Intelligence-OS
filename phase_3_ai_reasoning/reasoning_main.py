from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

from reasoning_config import (
    EMOTION_MANIFEST_CANDIDATES,
    FLAGGED_CALLS_PATH,
    PROCESSING_LOG_HEADERS,
    PROCESSING_LOG_PATH,
    REASONING_MANIFEST_PATH,
    REASONING_OUTPUT_DIR,
    RUNTIME_LOG_PATH,
    TRANSCRIPT_MANIFEST_CANDIDATES,
    ensure_phase_directories,
)
from reasoning_engines.confidence_checker import ConfidenceChecker
from reasoning_engines.conversion_engine import ConversionEngine
from reasoning_engines.intent_engine import IntentEngine
from reasoning_engines.objection_engine import ObjectionEngine
from reasoning_engines.risk_engine import RiskEngine
from shared.json_utils import read_json, write_json
from shared.logging_utils import TerminalUI, append_csv_row


def main() -> int:
    ensure_phase_directories()
    terminal = TerminalUI(RUNTIME_LOG_PATH)
    terminal.rule("GEW Intelligence OS - Phase 4 AI Reasoning", style="bold yellow")

    transcripts = _load_manifests(TRANSCRIPT_MANIFEST_CANDIDATES, terminal)
    emotions = _load_manifests(EMOTION_MANIFEST_CANDIDATES, terminal)

    if not transcripts:
        terminal.warning("No transcripts found. Nothing to reason about.")
        return 0

    terminal.info(f"Loaded {len(transcripts)} transcripts and {len(emotions)} emotion records.")

    objection_engine = ObjectionEngine(logger=terminal)
    intent_engine = IntentEngine(logger=terminal)
    risk_engine = RiskEngine(logger=terminal)
    conversion_engine = ConversionEngine(logger=terminal)

    manifest: list[dict[str, object]] = []
    flagged_calls: list[dict[str, Any]] = []
    workload = list(transcripts.values())[:100]

    with terminal.build_progress() as progress:
        task = progress.add_task("Running AI reasoning", total=len(workload))
        for sequence, transcript_entry in enumerate(workload, start=1):
            call_id = str(transcript_entry.get("call_id", "")).strip()
            transcript_path = Path(str(transcript_entry.get("output_path", "")).strip())
            started_at = time.perf_counter()
            terminal.rule(f"[{sequence}/{len(workload)}] REASON {call_id}", style="bold yellow")

            try:
                transcript_text = _load_transcript_text(transcript_path)
                emotion_data = emotions.get(call_id, {})
                if not transcript_text.strip():
                    raise ValueError("Empty transcript")

                objections = objection_engine.analyze(call_id, transcript_text)
                intent = intent_engine.analyze(call_id, transcript_text, emotion_data)
                risk = risk_engine.analyze(call_id, transcript_text, objections, emotion_data)
                conversion = conversion_engine.analyze(call_id, transcript_text, intent, risk)

                obj_check = ConfidenceChecker.check_objection_quality(objections)
                intent_check = ConfidenceChecker.check_intent_score(intent)
                risk_check = ConfidenceChecker.check_risk_assessment(risk)
                quality_check = ConfidenceChecker.summarize(obj_check, intent_check, risk_check)

                reasoning_payload = {
                    "call_id": call_id,
                    "transcript_path": str(transcript_path),
                    "reasoning_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "objections": objections,
                    "intent_analysis": intent,
                    "risk_assessment": risk,
                    "conversion_insight": conversion,
                    "quality_check": quality_check,
                    "processing_time_sec": round(time.perf_counter() - started_at, 2),
                }

                output_path = REASONING_OUTPUT_DIR / f"{call_id}.json"
                write_json(output_path, reasoning_payload)
                manifest.append(
                    {
                        "call_id": call_id,
                        "source_path": str(transcript_path),
                        "output_path": str(output_path),
                        "objection_count": len(objections),
                        "intent_score": intent.get("primary_intent_score", 0),
                        "intent_confidence": intent.get("intent_confidence", 0),
                        "risk_level": risk.get("overall_risk_level", ""),
                        "risk_score": risk.get("risk_score", 0),
                        "conversion_probability": conversion.get("conversion_probability", 0),
                        "quality_passed": quality_check.get("quality_check_passed", False),
                        "flagged": quality_check.get("manual_review_required", False),
                    }
                )

                if quality_check.get("manual_review_required"):
                    flagged_calls.append(
                        {
                            "call_id": call_id,
                            "reason": quality_check.get("summary", ""),
                            "issues": quality_check.get("issues", []),
                        }
                    )

                append_csv_row(
                    PROCESSING_LOG_PATH,
                    PROCESSING_LOG_HEADERS,
                    {
                        "call_id": call_id,
                        "status": "SUCCESS",
                        "objection_count": str(len(objections)),
                        "intent_score": str(intent.get("primary_intent_score", 0)),
                        "risk_level": str(risk.get("overall_risk_level", "")),
                        "conversion_probability": str(conversion.get("conversion_probability", 0)),
                        "quality_passed": str(quality_check.get("quality_check_passed", False)),
                        "processing_time_sec": str(reasoning_payload["processing_time_sec"]),
                        "error_message": "",
                    },
                )
            except Exception as exc:
                append_csv_row(
                    PROCESSING_LOG_PATH,
                    PROCESSING_LOG_HEADERS,
                    {
                        "call_id": call_id,
                        "status": "FAILED",
                        "objection_count": "0",
                        "intent_score": "0",
                        "risk_level": "",
                        "conversion_probability": "0",
                        "quality_passed": "false",
                        "processing_time_sec": str(round(time.perf_counter() - started_at, 2)),
                        "error_message": str(exc),
                    },
                )
                terminal.exception(call_id or "UNKNOWN_CALL", str(exc), exc)
            finally:
                progress.advance(task)

    write_json(REASONING_MANIFEST_PATH, manifest)
    if flagged_calls:
        write_json(FLAGGED_CALLS_PATH, flagged_calls)

    terminal.success(
        f"Phase 4 completed. Processed {len(manifest)} calls. "
        f"{sum(1 for item in manifest if item.get('quality_passed'))} passed quality checks."
    )
    return 0


def _load_manifests(candidates: list[Path], terminal: TerminalUI) -> dict[str, dict[str, Any]]:
    for candidate in candidates:
        payload = read_json(candidate, default=None)
        if not payload:
            continue

        terminal.info(f"Loaded manifest from {candidate}")
        if isinstance(payload, list):
            return {
                str(item.get("call_id", "")).strip(): item
                for item in payload
                if isinstance(item, dict) and str(item.get("call_id", "")).strip()
            }
        if isinstance(payload, dict):
            return {
                str(key).strip(): value
                for key, value in payload.items()
                if isinstance(value, dict)
            }

    terminal.warning(f"No manifest found in candidates: {[str(candidate) for candidate in candidates]}")
    return {}


def _load_transcript_text(transcript_path: Path) -> str:
    if not transcript_path.exists():
        return ""
    if transcript_path.suffix.lower() != ".json":
        return transcript_path.read_text(encoding="utf-8")

    payload = read_json(transcript_path, default={}) or {}
    transcript_value = payload.get("transcript", "")
    if isinstance(transcript_value, str):
        return transcript_value
    if isinstance(transcript_value, list):
        fragments: list[str] = []
        for segment in transcript_value:
            if not isinstance(segment, dict):
                continue
            timestamp = str(segment.get("timestamp", "")).strip()
            text = str(segment.get("text", "")).strip()
            fragments.append(f"{timestamp} {text}".strip() if timestamp else text)
        return "\n".join(fragment for fragment in fragments if fragment)
    return ""


if __name__ == "__main__":
    sys.exit(main())
