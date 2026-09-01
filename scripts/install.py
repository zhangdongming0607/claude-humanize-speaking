#!/usr/bin/env python3
"""Development checkout wrapper for the packaged CLI."""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from claude_humanize_speaking.cli import main  # noqa: E402


if __name__ == "__main__":
    main()
