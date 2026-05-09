from __future__ import annotations

import sys

from .decision_engine.main import main as decision_main


def main(argv: list[str] | None = None) -> int:
    return decision_main(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
