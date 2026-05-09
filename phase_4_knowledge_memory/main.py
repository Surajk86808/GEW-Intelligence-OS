from __future__ import annotations

import sys

from .memory.main import main as knowledge_main


def main(argv: list[str] | None = None) -> int:
    return knowledge_main(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
