#!/usr/bin/env python3
"""Standalone Mediator control center."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def launch_gui_dashboard() -> str:
    repo_root = Path(__file__).resolve().parent
    gui_path = repo_root / "my-ai-framework" / "ui" / "mediator_gui.py"
    if not gui_path.exists():
        return f"GUI file not found: {gui_path}"

    process = subprocess.Popen([sys.executable, str(gui_path)], cwd=str(repo_root))
    return f"Launched multi-project desktop dashboard (PID: {process.pid})"


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


def print_narrative_log_tail(line_count: int = 10) -> None:
    log_path = Path(__file__).resolve().parent / "my-ai-framework" / "logs" / "change_explanations.txt"
    if not log_path.exists():
        print("No narrative log found.")
        return

    print("\n--- Latest Narrative Log ---")
    try:
        lines = log_path.read_text(encoding="utf-8").splitlines()
        tail = lines[-line_count:]
        if tail:
            print("\n".join(tail))
        else:
            print("(Narrative log is empty)")
    except OSError as exc:
        print(f"Could not read narrative log: {exc}")


def _interactive_loop() -> int:
    while True:
        print("\n==============================")
        print("      Mediator Control Center")
        print("==============================")
        print("1) Analyze backend architecture")
        print("2) Sync architecture")
        print("3) Edit a file")
        print("4) Run custom mediator command")
        print("5) View latest narrative log")
        print("6) Open multi-project desktop dashboard")
        print("0) Exit")
        print("==============================")

        try:
            choice = input("Select an option: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if choice == "1":
            print("\n" + run_task("analyze backend architecture") + "\n")
        elif choice == "2":
            print("\n" + run_task("sync architecture") + "\n")
        elif choice == "3":
            path = input("File path: ").strip()
            old = input("Old text: ").strip()
            new = input("New text: ").strip()
            command = f"edit|{path}|{old}|{new}"
            print("\n" + run_task(command) + "\n")
        elif choice == "4":
            command = input("Mediator command: ").strip()
            if not command:
                print("No command entered.")
                continue
            print("\n" + run_task(command) + "\n")
        elif choice == "5":
            print_narrative_log_tail(10)
        elif choice == "6":
            print("\n" + launch_gui_dashboard() + "\n")
        elif choice == "0":
            print("Goodbye.")
            break
        else:
            print("Invalid selection.")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Mediator Control Center")
    parser.add_argument("task", nargs="*", help="Optional one-shot task to run.")
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch the multi-project desktop dashboard.",
    )
    parser.add_argument(
        "--no-log-tail",
        action="store_true",
        help="Do not print narrative log tail after one-shot task execution.",
    )
    args = parser.parse_args()

    if args.gui:
        print(launch_gui_dashboard())
        return 0

    if args.task:
        task = " ".join(args.task).strip()
        if not task:
            return 0
        result = run_task(task)
        print(result)
        if not args.no_log_tail:
            print_narrative_log_tail(5)
        return 0

    return _interactive_loop()


if __name__ == "__main__":
    raise SystemExit(main())
