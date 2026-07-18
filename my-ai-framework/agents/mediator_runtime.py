#!/usr/bin/env python3
"""Runtime routing hook for MediatorAI bridge integration."""

from __future__ import annotations

import sys
import json
from pathlib import Path

_framework_root = Path(__file__).resolve().parents[1]
if str(_framework_root) not in sys.path:
    sys.path.insert(0, str(_framework_root))

from status_channel import send_status
from code_editor import edit_code


def _analyze_architecture_snapshot() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    arch_path = repo_root / "architecture-generator" / "architecture.json"
    report_path = repo_root / "architecture-generator" / "output" / "mediator_analysis_report.txt"

    if not arch_path.exists():
        return f"Architecture file not found: {arch_path}"

    with arch_path.open("r", encoding="utf-8") as file_handle:
        data = json.load(file_handle)

    service = data.get("service", {}) if isinstance(data, dict) else {}
    controllers = service.get("controllers", []) if isinstance(service, dict) else []
    services = service.get("services", []) if isinstance(service, dict) else []
    repositories = service.get("repositories", []) if isinstance(service, dict) else []
    dtos = service.get("dtos", []) if isinstance(service, dict) else []

    lines = [
        "MediatorAI Architecture Analysis",
        "==============================",
        f"controllers: {len(controllers)}",
        f"services: {len(services)}",
        f"repositories: {len(repositories)}",
        f"dtos: {len(dtos)}",
    ]

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f"Wrote architecture summary to {report_path}"


def _create_mediator_app() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    app_path = repo_root / "mediator_app.py"

    app_code = '''#!/usr/bin/env python3
"""Standalone Mediator control center."""

from __future__ import annotations

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
            print("\\nRecent narrative log lines:")
            print("\\n".join(tail))
    except OSError:
        pass


def main() -> int:
    print("=== Mediator Control Center ===")
    print("Type a command (analyze, sync, edit, deploy) or 'exit' to quit.\\n")

    while True:
        try:
            task = input("Mediator> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\\nGoodbye.")
            break

        if task.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break
        if not task:
            continue

        result = run_task(task)
        print("\\nResult:\\n" + result + "\\n")
        print_latest_narrative_lines()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

    app_path.write_text(app_code, encoding="utf-8")
    return f"Created standalone mediator app at {app_path}"


def handle_task(task: str) -> str:
    text = (task or "").strip()
    if not text:
        send_status("MediatorAI", "Error", "Received empty task")
        return "No task provided."

    send_status("MediatorAI", "Start", f"Task received: {text}")
    lowered = text.lower()

    if lowered.startswith("edit|"):
        send_status("MediatorAI", "Route", "Routing task to code_editor")
        parts = text.split("|", 3)
        if len(parts) != 4:
            send_status("MediatorAI", "Error", "Invalid edit command format")
            return "Invalid edit command format. Use: edit|path|old_text|new_text"

        _cmd, file_path, old_text, new_text = parts
        initiator_agent = "MediatorAI"
        result = edit_code(file_path.strip(), old_text, new_text, initiator_agent)
        if result.startswith(f"{initiator_agent} edited "):
            send_status("MediatorAI", "Change", f"Edited file: {file_path.strip()}")
            send_status(initiator_agent, "Change", result)
            send_status("MediatorAI", "Complete", f"Task '{text}' finished successfully")
        else:
            send_status("MediatorAI", "Error", result)
        return result

    routes = [
        ("analy", "AnalyzerAgent"),
        ("architect", "ArchitectureAgent"),
        ("sync", "SyncAgent"),
        ("test", "TestAgent"),
        ("doc", "DocumentationAgent"),
        ("deploy", "DeploymentAgent"),
        ("monitor", "MonitorAgent"),
        ("audit", "CodeAuditAgent"),
        ("resource", "ResourceMonitorAgent"),
        ("valid", "ValidatorAgent"),
        ("file", "FileManagerAgent"),
        ("gen", "GeneratorAgent"),
        ("build", "GeneratorAgent"),
    ]

    selected = "MediatorAI"
    for token, agent_name in routes:
        if token in lowered:
            selected = agent_name
            break

    send_status("MediatorAI", "Route", f"Routing task to {selected}")
    send_status(selected, "Change", "Accepted task from MediatorAI")

    result = f"Framework MediatorAI routed task to {selected}: {text}"
    if selected == "AnalyzerAgent":
        result = _analyze_architecture_snapshot()
        send_status("AnalyzerAgent", "Change", "Generated mediator architecture analysis report")

    if any(
        phrase in lowered
        for phrase in (
            "own program",
            "standalone app",
            "mediator app",
            "control center",
            "easier to navigate",
        )
    ):
        send_status("MediatorAI", "Route", "Routing task to GeneratorAgent for app scaffold")
        result = _create_mediator_app()
        send_status("GeneratorAgent", "Change", "Created mediator_app.py scaffold")

    send_status("MediatorAI", "Complete", f"Task '{text}' finished successfully")
    return result
