#!/usr/bin/env python3
"""Standalone Mediator control center."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_task(task: str) -> str:
    repo_root = Path(__file__).resolve().parent
    bridge_path = repo_root / "mediator_bridge.py"

    proc = subprocess.run(
        [sys.executable, str(bridge_path), task],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )
    output = (proc.stdout or "").strip()
    error = (proc.stderr or "").strip()
    if output:
        return output
    if error:
        return error
    return f"Bridge exited with code {proc.returncode}"


def print_latest_narrative_lines(line_count: int = 8) -> None:
    repo_root = Path(__file__).resolve().parent
    narrative_path = repo_root / "my-ai-framework" / "logs" / "change_explanations.txt"
    if not narrative_path.exists():
        return

    try:
        lines = narrative_path.read_text(encoding="utf-8").splitlines()
        tail = lines[-line_count:]
        if tail:
            print("\nRecent narrative log lines:")
            print("\n".join(tail))
    except OSError:
        pass


def _interactive_loop() -> int:
    print("=== Mediator Control Center ===")
    print("Type a command (analyze, sync, edit, deploy) or 'exit' to quit.\n")

    while True:
        try:
            task = input("Mediator> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if task.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break
        if not task:
            continue

        result = run_task(task)
        print("\nResult:\n" + result + "\n")
        print_latest_narrative_lines()

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Mediator Control Center")
    parser.add_argument("task", nargs="*", help="Optional one-shot task to run.")
    parser.add_argument(
        "--no-log-tail",
        action="store_true",
        help="Do not print narrative log tail after one-shot task execution.",
    )
    args = parser.parse_args()

    if args.task:
        task = " ".join(args.task).strip()
        if not task:
            return 0
        result = run_task(task)
        print(result)
        if not args.no_log_tail:
            print_latest_narrative_lines()
        return 0

    return _interactive_loop()


if __name__ == "__main__":
    raise SystemExit(main())
