#!/usr/bin/env python3
"""Root launcher for the VS Code mediator bridge script."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    bridge_script = repo_root / ".github" / "agents" / "mediator_bridge.py"

    if not bridge_script.exists():
        print(f"Bridge script not found: {bridge_script}")
        return 1

    sys.argv[0] = str(bridge_script)
    runpy.run_path(str(bridge_script), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
