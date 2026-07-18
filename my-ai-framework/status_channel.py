#!/usr/bin/env python3
"""Lightweight local status socket for agent progress updates."""

from __future__ import annotations

import datetime
import json
import socket
import threading
from typing import Any
from pathlib import Path
import re

HOST = "127.0.0.1"
PORT = 5055
LOG_FILE = Path(__file__).resolve().parent / "logs" / "agent_activity.log"
DETAILED_LOG_FILE = Path(__file__).resolve().parent / "logs" / "agent_activity_detailed.log"
HUMAN_LOG_FILE = Path(__file__).resolve().parent / "logs" / "change_explanations.txt"
COMMAND_REPORT_DIR = Path(__file__).resolve().parent / "logs" / "command_reports"
_server_started = False
_server_lock = threading.Lock()
_server_socket: socket.socket | None = None
_accept_thread: threading.Thread | None = None
_stop_event = threading.Event()
_command_context: dict[str, Any] | None = None
_command_lock = threading.Lock()


def _write_log(entry: dict[str, object]) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as file_handle:
        file_handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _write_detailed_log(entry: dict[str, Any]) -> None:
    DETAILED_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    timestamp = str(entry.get("timestamp", ""))
    agent = str(entry.get("agent", "Unknown"))
    change_type = str(entry.get("change_type", "Message"))
    details = str(entry.get("details", ""))
    source = str(entry.get("source", "status_channel"))
    initiator = str(entry.get("initiator_agent", entry.get("agent", "Unknown")))
    offline = bool(entry.get("offline", False))
    metadata = entry.get("metadata")

    lines = [
        f"[{timestamp}] agent={agent} initiator={initiator} type={change_type} source={source} offline={offline}",
        f"details: {details}",
    ]
    if metadata is not None:
        lines.append(f"metadata: {json.dumps(metadata, ensure_ascii=False)}")
    lines.append("-")

    with DETAILED_LOG_FILE.open("a", encoding="utf-8") as file_handle:
        file_handle.write("\n".join(lines) + "\n")


def _write_human_log(entry: dict[str, Any]) -> None:
    HUMAN_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    timestamp = str(entry.get("timestamp", ""))
    agent = str(entry.get("agent", "Unknown"))
    initiator = str(entry.get("initiator_agent", agent))
    change_type = str(entry.get("change_type", "Message"))
    details = str(entry.get("details", ""))
    source = str(entry.get("source", "status_channel"))
    metadata = entry.get("metadata")

    where_text = f"the {agent} event pipeline"
    if isinstance(metadata, dict) and metadata.get("file_path"):
        where_text = str(metadata.get("file_path"))

    why_text = "to keep system state and audit trails consistent"
    change_type_lower = change_type.lower()
    if change_type_lower == "start":
        why_text = "to mark the beginning of a requested task"
    elif change_type_lower == "route":
        why_text = "to delegate work to the most relevant agent or subsystem"
    elif change_type_lower == "change":
        why_text = "to capture a concrete state or content change"
    elif change_type_lower == "edit":
        why_text = "to persist code edits with traceability for future investigation"
    elif change_type_lower == "complete":
        why_text = "to confirm successful completion of the task"
    elif change_type_lower == "error":
        why_text = "to record failures for diagnosis and remediation"

    paragraph = (
        f"On {timestamp}, {initiator} initiated a {change_type} event that was recorded by {agent} "
        f"through {source}. The change was: {details}. This affected {where_text}, and it was recorded {why_text}."
    )
    if isinstance(metadata, dict) and metadata:
        paragraph += f" Additional context: {json.dumps(metadata, ensure_ascii=False)}."

    with HUMAN_LOG_FILE.open("a", encoding="utf-8") as file_handle:
        file_handle.write(paragraph + "\n\n")


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:50] if slug else "command"


def start_command_report(command_text: str, initiator_agent: str = "MediatorAI") -> str:
    """Begin collecting events for a single mediator command."""
    global _command_context
    with _command_lock:
        command_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        _command_context = {
            "command_id": command_id,
            "command_text": command_text,
            "initiator_agent": initiator_agent,
            "started_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "events": [],
        }
        return command_id


def _agent_status(events: list[dict[str, Any]]) -> dict[str, str]:
    status: dict[str, str] = {}
    by_agent: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        agent = str(event.get("agent", "Unknown"))
        by_agent.setdefault(agent, []).append(event)

    for agent, agent_events in by_agent.items():
        types = {str(e.get("change_type", "")).lower() for e in agent_events}
        if "error" in types:
            status[agent] = "Not completed (error encountered)"
        elif "complete" in types:
            status[agent] = "Completed"
        elif "change" in types or "edit" in types or "route" in types:
            status[agent] = "Contributed changes"
        elif "start" in types:
            status[agent] = "Started"
        else:
            status[agent] = "Observed"
    return status


def _next_steps(events: list[dict[str, Any]], command_result: str) -> list[str]:
    lowered_result = command_result.lower()
    event_types = {str(e.get("change_type", "")).lower() for e in events}
    steps: list[str] = []

    if "error" in event_types or "invalid" in lowered_result or "not found" in lowered_result:
        steps.append("Review error details in agent_activity_detailed.log and correct command inputs.")
    else:
        steps.append("Review generated artifacts or edited files to confirm expected results.")

    if any("analy" in str(e.get("details", "")).lower() for e in events):
        steps.append("If analysis looks good, run a sync or generation command to apply follow-up updates.")

    if any(str(e.get("agent", "")) == "CodeEditor" for e in events):
        steps.append("Run tests or lint checks after code edits to validate behavior.")

    steps.append("Use change_explanations.txt for human narrative and agent_activity.log for machine parsing.")
    return steps


def finalize_command_report(command_result: str) -> Path | None:
    """Finalize and write one detailed report for the active command."""
    global _command_context
    with _command_lock:
        if _command_context is None:
            return None

        context = _command_context
        _command_context = None

    command_id = str(context.get("command_id", "unknown"))
    command_text = str(context.get("command_text", ""))
    initiator_agent = str(context.get("initiator_agent", "MediatorAI"))
    started_at = str(context.get("started_at", ""))
    finished_at = datetime.datetime.now().isoformat(timespec="seconds")
    events: list[dict[str, Any]] = list(context.get("events", []))

    status_by_agent = _agent_status(events)
    involved_agents = sorted(status_by_agent.keys())
    next_steps = _next_steps(events, command_result)

    summary_lines = [
        "Main changes and status updates:",
    ]
    if not events:
        summary_lines.append("- No status events were captured for this command.")
    else:
        for event in events:
            ts = str(event.get("timestamp", ""))
            agent = str(event.get("agent", "Unknown"))
            ctype = str(event.get("change_type", "Message"))
            details = str(event.get("details", ""))
            summary_lines.append(f"- [{ts}] {agent} {ctype}: {details}")

    agent_lines = ["Agents involved and objective status:"]
    if not involved_agents:
        agent_lines.append("- No agents were identified from events.")
    else:
        for agent in involved_agents:
            agent_lines.append(f"- {agent}: {status_by_agent.get(agent, 'Unknown')}")

    next_lines = ["Suggested next steps:"] + [f"- {step}" for step in next_steps]

    report_text = "\n\n".join(
        [
            "Mediator Command Report",
            (
                f"Command ID: {command_id}\n"
                f"Started: {started_at}\n"
                f"Finished: {finished_at}\n"
                f"Initiator: {initiator_agent}\n"
                f"Command: {command_text}"
            ),
            "Command result:\n" + command_result,
            "\n".join(summary_lines),
            "\n".join(agent_lines),
            "\n".join(next_lines),
        ]
    ) + "\n"

    COMMAND_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    file_name = f"{command_id}-{_slugify(command_text)}.txt"
    report_path = COMMAND_REPORT_DIR / file_name
    report_path.write_text(report_text, encoding="utf-8")
    return report_path


def record_event(
    agent: str,
    change_type: str,
    details: str,
    *,
    source: str = "status_channel",
    initiator_agent: str | None = None,
    metadata: dict[str, Any] | None = None,
    offline: bool = False,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "agent": agent,
        "change_type": change_type,
        "details": details,
        "source": source,
        "initiator_agent": initiator_agent or agent,
        "offline": offline,
    }
    if metadata is not None:
        entry["metadata"] = metadata

    _write_log(entry)
    _write_detailed_log(entry)
    _write_human_log(entry)
    with _command_lock:
        if _command_context is not None:
            _command_context.setdefault("events", []).append(entry)
    return entry


def start_status_server() -> None:
    """Start a non-blocking local status server once per process."""
    global _server_started, _server_socket, _accept_thread

    with _server_lock:
        if _server_started:
            return

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(5)
        _stop_event.clear()
        _server_socket = server
        _server_started = True

    print(f"[StatusChannel] Listening on {HOST}:{PORT}")

    def accept_loop() -> None:
        while not _stop_event.is_set():
            try:
                conn, _addr = server.accept()
            except OSError:
                break
            threading.Thread(target=handle_client, args=(conn,), daemon=True).start()

    def handle_client(conn: socket.socket) -> None:
        with conn:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                message = data.decode(errors="replace").strip()
                print(f"[StatusChannel] {message}")
                try:
                    agent, change_type, details = message.split("|", 2)
                except ValueError:
                    agent, change_type, details = "Unknown", "Message", message
                record_event(agent, change_type, details, source="socket")

    _accept_thread = threading.Thread(target=accept_loop, daemon=True)
    _accept_thread.start()


def stop_status_server() -> None:
    """Stop the local status server if it is running."""
    global _server_started, _server_socket, _accept_thread

    with _server_lock:
        if not _server_started:
            return

        _stop_event.set()
        if _server_socket is not None:
            try:
                _server_socket.close()
            except OSError:
                pass

        if _accept_thread is not None:
            _accept_thread.join(timeout=0.5)

        _accept_thread = None
        _server_socket = None
        _server_started = False


def send_status(agent: str, change_type: str, details: str) -> None:
    """Send a best-effort status message and persist even when offline."""
    message = f"{agent}|{change_type}|{details}"
    try:
        with socket.create_connection((HOST, PORT), timeout=2) as sock:
            sock.sendall(message.encode())
    except OSError:
        record_event(agent, change_type, details, source="fallback", offline=True)
