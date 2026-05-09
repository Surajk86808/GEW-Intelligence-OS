from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PHASE_DIRS = [
    "phase_1_audio_ingestion_transcription",
    "phase_2_enrichment_structured_extraction",
    "phase_3_ai_reasoning",
    "phase_4_knowledge_memory",
    "phase_5_query_intelligence",
]
DISALLOWED_FILENAME_TOKENS = {
    "phase_1_audio_ingestion_transcription": {"emotion", "reason", "vector", "embed"},
    "phase_2_enrichment_structured_extraction": {"vector", "embed"},
    "phase_3_ai_reasoning": {"ffmpeg", "audio_downloader", "transcrib"},
    "phase_4_knowledge_memory": {"ffmpeg", "audio_downloader", "transcrib"},
    "phase_5_query_intelligence": {"ffmpeg", "audio_downloader"},
}


def main() -> int:
    violations: list[str] = []
    for phase_dir in PHASE_DIRS:
        directory = ROOT / phase_dir
        for file_path in directory.rglob("*.py"):
            relative = file_path.relative_to(ROOT)
            if "__pycache__" in relative.parts:
                continue
            violations.extend(_check_filename(relative, phase_dir))
            violations.extend(_check_imports(file_path, phase_dir))

    if violations:
        print("Architecture validation failed:")
        for violation in violations:
            print(f"- {violation}")
        return 1

    print("Architecture validation passed.")
    return 0


def _check_filename(relative: Path, phase_dir: str) -> list[str]:
    name = relative.stem.lower()
    issues = []
    for token in DISALLOWED_FILENAME_TOKENS.get(phase_dir, set()):
        if token in name:
            issues.append(f"{relative} contains disallowed token '{token}' for {phase_dir}")
    return issues


def _check_imports(file_path: Path, phase_dir: str) -> list[str]:
    issues = []
    module = ast.parse(file_path.read_text(encoding="utf-8"))
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            for alias in node.names:
                issues.extend(_validate_import_target(file_path, phase_dir, alias.name))
        elif isinstance(node, ast.ImportFrom) and node.module:
            issues.extend(_validate_import_target(file_path, phase_dir, node.module))
    return issues


def _validate_import_target(file_path: Path, phase_dir: str, module_name: str) -> list[str]:
    issues = []
    for candidate in PHASE_DIRS:
        if candidate == phase_dir:
            continue
        if module_name == candidate or module_name.startswith(f"{candidate}."):
            issues.append(f"{file_path.relative_to(ROOT)} imports {module_name}; phases must communicate through outputs, not code imports.")
    return issues


if __name__ == "__main__":
    sys.exit(main())
