#!/usr/bin/env python3
"""Simple text replacement helper with audit logging."""

from __future__ import annotations

import datetime
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent / "logs" / "code_edits.log"

from status_channel import record_event


def edit_code(
    file_path: str,
    old_text: str,
    new_text: str,
    initiator_agent: str = "Unknown",
) -> str:
    path = Path(file_path)
    if not path.is_absolute():
        repo_root = Path(__file__).resolve().parents[1]
        path = repo_root / path

    if not path.exists():
        return f"File not found: {path}"

    content = path.read_text(encoding="utf-8")
    if old_text not in content:
        return f"Target text not found in {path}"

    updated = content.replace(old_text, new_text)
    path.write_text(updated, encoding="utf-8")

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as log_handle:
        timestamp = datetime.datetime.now().isoformat(timespec="seconds")
        log_handle.write(
            f"{timestamp} | {initiator_agent} | {path} | replaced '{old_text}' with '{new_text}'\n"
        )

    record_event(
        agent="CodeEditor",
        change_type="Edit",
        details=f"Replaced text in {path}",
        source="code_editor",
        initiator_agent=initiator_agent,
        metadata={
            "file_path": str(path),
            "old_text": old_text,
            "new_text": new_text,
        },
    )

    return f"{initiator_agent} edited {path}: replaced '{old_text}' with '{new_text}'"
