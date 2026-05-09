from __future__ import annotations

import sys
from pathlib import Path

PHASE_DIR = Path(__file__).resolve().parent
if str(PHASE_DIR) not in sys.path:
    sys.path.insert(0, str(PHASE_DIR))

from ingestion.main import main as ingestion_main
from transcription.main import main as transcription_main


def main(argv: list[str] | None = None) -> int:
    result = ingestion_main(argv)
    if result != 0:
        return result
    return transcription_main(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
