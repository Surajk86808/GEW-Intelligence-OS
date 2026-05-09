from __future__ import annotations

import sys
from pathlib import Path

PHASE_DIR = Path(__file__).resolve().parent
if str(PHASE_DIR) not in sys.path:
    sys.path.insert(0, str(PHASE_DIR))

from phase_3_voice_intelligence.main import main as enrichment_main


def main() -> int:
    return enrichment_main()


if __name__ == "__main__":
    sys.exit(main())

