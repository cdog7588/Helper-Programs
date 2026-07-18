#!/usr/bin/env python3
"""Figma-driven Mediator desktop UI (PySide6)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import requests
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from figma_config import get_figma_file_key, get_figma_token  # type: ignore
else:
    from .figma_config import get_figma_file_key, get_figma_token


def fetch_figma_file() -> dict[str, Any]:
    token = get_figma_token()
    file_key = get_figma_file_key()
    if not token or not file_key:
        raise RuntimeError(
            "Missing Figma config. Set FIGMA_TOKEN and FIGMA_FILE_KEY environment variables."
        )

    url = f"https://api.figma.com/v1/files/{file_key}"
    headers = {"X-Figma-Token": token}
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    return response.json()


def find_named_nodes(figma_json: dict[str, Any]) -> dict[str, dict[str, Any]]:
    named: dict[str, dict[str, Any]] = {}

    def walk(node: dict[str, Any]) -> None:
        name = node.get("name")
        if isinstance(name, str) and name:
            named[name] = node
        children = node.get("children", [])
        if isinstance(children, list):
            for child in children:
                if isinstance(child, dict):
                    walk(child)

    root = figma_json.get("document")
    if isinstance(root, dict):
        walk(root)
    return named


def run_mediator_command(command: str) -> str:
    repo_root = Path(__file__).resolve().parents[2]
    bridge_path = repo_root / "mediator_bridge.py"
    if not bridge_path.exists():
        return f"Bridge script not found: {bridge_path}"

    process = subprocess.run(
        [sys.executable, str(bridge_path), command],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )
    stdout = (process.stdout or "").strip()
    stderr = (process.stderr or "").strip()
    if stdout:
        return stdout
    if stderr:
        return stderr
    return f"Mediator command exited with code {process.returncode}"


class MediatorWindow(QWidget):
    def __init__(self, named_nodes: dict[str, dict[str, Any]] | None = None) -> None:
        super().__init__()
        self.named_nodes = named_nodes or {}

        self.setWindowTitle("Mediator Control Center")
        self.resize(1100, 760)

        root_layout = QHBoxLayout()
        self.setLayout(root_layout)

        command_box = QGroupBox("Commands")
        command_layout = QVBoxLayout()
        command_box.setLayout(command_layout)

        output_box = QGroupBox("Output and Logs")
        output_layout = QVBoxLayout()
        output_box.setLayout(output_layout)

        root_layout.addWidget(command_box, 1)
        root_layout.addWidget(output_box, 3)

        self.output_label = QLabel("Run a command to see output.")
        self.output_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.output_label.setWordWrap(True)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)

        output_layout.addWidget(self.output_label)
        output_layout.addWidget(self.log_view)

        self.build_buttons(command_layout)
        self.refresh_log_tail()

    def build_buttons(self, layout: QVBoxLayout) -> None:
        has = self.named_nodes.__contains__

        if has("btn_analyze") or not self.named_nodes:
            btn = QPushButton("Analyze backend architecture")
            btn.clicked.connect(lambda: self.run_command("analyze backend architecture"))
            layout.addWidget(btn)

        if has("btn_sync") or not self.named_nodes:
            btn = QPushButton("Sync architecture")
            btn.clicked.connect(lambda: self.run_command("sync architecture"))
            layout.addWidget(btn)

        if has("btn_edit") or not self.named_nodes:
            btn = QPushButton("Edit file")
            btn.clicked.connect(self.run_edit_command)
            layout.addWidget(btn)

        if has("btn_custom") or not self.named_nodes:
            btn = QPushButton("Run custom command")
            btn.clicked.connect(self.run_custom_command)
            layout.addWidget(btn)

        refresh = QPushButton("Refresh narrative log")
        refresh.clicked.connect(self.refresh_log_tail)
        layout.addWidget(refresh)

        layout.addStretch(1)

    def run_command(self, command: str) -> None:
        result = run_mediator_command(command)
        self.output_label.setText(f"Command: {command}\n\nResult:\n{result}")
        self.refresh_log_tail()

    def run_custom_command(self) -> None:
        command, ok = QInputDialog.getText(self, "Mediator Command", "Enter mediator command:")
        if ok and command.strip():
            self.run_command(command.strip())

    def run_edit_command(self) -> None:
        file_path, ok_path = QInputDialog.getText(self, "Edit Command", "File path:")
        if not ok_path or not file_path.strip():
            return

        old_text, ok_old = QInputDialog.getText(self, "Edit Command", "Old text:")
        if not ok_old:
            return

        new_text, ok_new = QInputDialog.getText(self, "Edit Command", "New text:")
        if not ok_new:
            return

        command = f"edit|{file_path.strip()}|{old_text}|{new_text}"
        self.run_command(command)

    def refresh_log_tail(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        narrative_log = repo_root / "my-ai-framework" / "logs" / "change_explanations.txt"
        if not narrative_log.exists():
            self.log_view.setPlainText("No narrative log found yet.")
            return

        try:
            lines = narrative_log.read_text(encoding="utf-8").splitlines()
            tail = lines[-40:]
            self.log_view.setPlainText("\n".join(tail) if tail else "Narrative log is empty.")
        except OSError as exc:
            self.log_view.setPlainText(f"Could not read narrative log: {exc}")


def main() -> int:
    figma_nodes: dict[str, dict[str, Any]] = {}
    figma_warning = ""

    try:
        figma_json = fetch_figma_file()
        figma_nodes = find_named_nodes(figma_json)
    except Exception as exc:  # noqa: BLE001
        figma_warning = str(exc)

    app = QApplication(sys.argv)
    window = MediatorWindow(figma_nodes)
    if figma_warning:
        QMessageBox.information(
            window,
            "Figma Config Notice",
            "Running with default menu because Figma could not be loaded.\n\n"
            + figma_warning
            + "\n\nSet FIGMA_TOKEN and FIGMA_FILE_KEY to enable dynamic mapping.",
        )
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
