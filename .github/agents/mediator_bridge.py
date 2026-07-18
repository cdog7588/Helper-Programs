#!/usr/bin/env python3
"""Bridge from VS Code wrapper context into framework Mediator runtime."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def push_to_figma_plugin(
    payload: dict[str, Any],
    endpoint: str = "http://127.0.0.1:8080/figma-plugin",
    timeout: float = 5.0,
) -> str:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_body = response.read().decode("utf-8", errors="ignore")
            return f"Figma plugin push succeeded ({response.status}). {response_body[:240]}"
    except urllib.error.URLError as exc:
        return f"Figma plugin push failed: {exc}"


def activate_framework_mediator(task: str) -> str:
    repo_root = Path(__file__).resolve().parents[2]
    framework_root = repo_root / "my-ai-framework"
    runtime_path = repo_root / "my-ai-framework" / "agents" / "mediator_runtime.py"

    if str(framework_root) not in sys.path:
        sys.path.insert(0, str(framework_root))

    try:
        from status_channel import (  # type: ignore
            start_status_server,
            stop_status_server,
            start_command_report,
            finalize_command_report,
        )

        start_status_server()
    except Exception as exc:
        return f"Failed to start status channel: {exc}"

    start_command_report(task, initiator_agent="MediatorAI")

    if not runtime_path.exists():
        return f"Missing runtime module: {runtime_path}"

    spec = importlib.util.spec_from_file_location("framework_mediator_runtime", runtime_path)
    if spec is None or spec.loader is None:
        return f"Could not load runtime spec from: {runtime_path}"

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    handler = getattr(module, "handle_task", None)
    if not callable(handler):
        result_text = "Framework mediator runtime has no callable handle_task(task) function."
        report_path = finalize_command_report(result_text)
        stop_status_server()
        if report_path is not None:
            return f"{result_text}\nDetailed command report: {report_path}"
        return result_text

    try:
        result_text = str(handler(task))
        report_path = finalize_command_report(result_text)
        if report_path is not None:
            return f"{result_text}\nDetailed command report: {report_path}"
        return result_text
    except Exception as exc:
        result_text = f"Mediator runtime failed: {exc}"
        report_path = finalize_command_report(result_text)
        if report_path is not None:
            return f"{result_text}\nDetailed command report: {report_path}"
        return result_text
    finally:
        stop_status_server()


def main() -> int:
    parser = argparse.ArgumentParser(description="Activate framework MediatorAI runtime.")
    parser.add_argument("task", nargs="?", help="Task text to route through framework MediatorAI.")
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run interactive chat mode.",
    )
    args = parser.parse_args()

    if args.interactive or not args.task:
        while True:
            try:
                task = input("MediatorAI> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if task.lower() in {"exit", "quit"}:
                break
            if not task:
                continue
            print(activate_framework_mediator(task))
        return 0

    print(activate_framework_mediator(args.task))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
