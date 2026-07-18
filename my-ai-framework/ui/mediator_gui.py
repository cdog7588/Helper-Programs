#!/usr/bin/env python3
"""Multi-project Mediator desktop UI (PySide6)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

APP_STATE_DIR = Path.home() / ".mediator_desktop"
PROJECTS_FILE = APP_STATE_DIR / "projects.json"


def load_projects() -> list[str]:
    if not PROJECTS_FILE.exists():
        return []
    try:
        data = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            projects = [str(Path(item).resolve()) for item in data if isinstance(item, str)]
            # Preserve user order while removing duplicates.
            deduped: list[str] = []
            seen = set()
            for project in projects:
                if project not in seen:
                    deduped.append(project)
                    seen.add(project)
            return deduped
    except (OSError, json.JSONDecodeError):
        pass
    return []


def save_projects(project_paths: list[str]) -> None:
    APP_STATE_DIR.mkdir(parents=True, exist_ok=True)
    PROJECTS_FILE.write_text(json.dumps(project_paths, indent=2), encoding="utf-8")


def parse_architecture(project_root: Path) -> tuple[str, str]:
    arch_path = project_root / "architecture-generator" / "architecture.json"
    if not arch_path.exists():
        return (
            "No architecture file found.",
            f"Expected architecture file at: {arch_path}",
        )

    try:
        data = json.loads(arch_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return (
            "Could not parse architecture file.",
            f"Error reading {arch_path}: {exc}",
        )

    service = data.get("service", {}) if isinstance(data, dict) else {}
    controllers = service.get("controllers", []) if isinstance(service, dict) else []
    services = service.get("services", []) if isinstance(service, dict) else []
    repositories = service.get("repositories", []) if isinstance(service, dict) else []
    dtos = service.get("dtos", []) if isinstance(service, dict) else []

    summary_lines = [
        "Backend Architecture Summary",
        "============================",
        f"Project: {project_root}",
        "",
        f"controllers: {len(controllers)}",
        f"services: {len(services)}",
        f"repositories: {len(repositories)}",
        f"dtos: {len(dtos)}",
    ]
    pretty_json = json.dumps(data, indent=2)
    return "\n".join(summary_lines), pretty_json


def detect_agents(project_root: Path) -> list[str]:
    agents: set[str] = set()
    for folder in (
        project_root / ".github" / "agents",
        project_root / "my-ai-framework" / "agents",
    ):
        if not folder.exists():
            continue
        for file_path in folder.glob("*.agent.md"):
            agents.add(file_path.stem.replace(".agent", ""))
    return sorted(agents)


def run_mediator_command(project_root: Path, command: str) -> str:
    bridge_path = project_root / "mediator_bridge.py"
    if not bridge_path.exists():
        return (
            "This project does not have mediator_bridge.py yet.\n"
            "You can still inspect architecture and agents, but command execution requires mediator runtime files."
        )

    process = subprocess.run(
        [sys.executable, str(bridge_path), command],
        capture_output=True,
        text=True,
        cwd=str(project_root),
    )
    stdout = (process.stdout or "").strip()
    stderr = (process.stderr or "").strip()
    if stdout:
        return stdout
    if stderr:
        return stderr
    return f"Mediator command exited with code {process.returncode}"


class ArchitectureWindow(QWidget):
    def __init__(self, project_root: Path) -> None:
        super().__init__()
        self.project_root = project_root
        self.setWindowTitle(f"Architecture - {project_root.name}")
        self.resize(980, 740)

        root_layout = QVBoxLayout()
        self.setLayout(root_layout)

        self.summary = QTextEdit()
        self.summary.setReadOnly(True)

        self.raw_json = QTextEdit()
        self.raw_json.setReadOnly(True)

        refresh_btn = QPushButton("Refresh Architecture")
        refresh_btn.clicked.connect(self.refresh)

        root_layout.addWidget(refresh_btn)
        root_layout.addWidget(QLabel("Summary"))
        root_layout.addWidget(self.summary, 1)
        root_layout.addWidget(QLabel("Raw architecture.json"))
        root_layout.addWidget(self.raw_json, 3)

        self.refresh()

    def refresh(self) -> None:
        summary_text, raw_json = parse_architecture(self.project_root)
        self.summary.setPlainText(summary_text)
        self.raw_json.setPlainText(raw_json)


class ActionsWindow(QWidget):
    def __init__(self, project_root: Path) -> None:
        super().__init__()
        self.project_root = project_root
        self.setWindowTitle(f"Agents and Actions - {project_root.name}")
        self.resize(980, 740)

        root_layout = QHBoxLayout()
        self.setLayout(root_layout)

        left_box = QGroupBox("Available Agents")
        left_layout = QVBoxLayout()
        left_box.setLayout(left_layout)

        right_box = QGroupBox("Actions and Output")
        right_layout = QVBoxLayout()
        right_box.setLayout(right_layout)

        root_layout.addWidget(left_box, 1)
        root_layout.addWidget(right_box, 2)

        self.agent_list = QListWidget()
        left_layout.addWidget(self.agent_list)

        for label, command in (
            ("Analyze Backend Architecture", "analyze backend architecture"),
            ("Sync Architecture", "sync architecture"),
            ("Run Custom Command", "__custom__"),
        ):
            btn = QPushButton(label)
            if command == "__custom__":
                btn.clicked.connect(self.run_custom_command)
            else:
                btn.clicked.connect(lambda _checked=False, c=command: self.run_command(c))
            right_layout.addWidget(btn)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        right_layout.addWidget(self.output, 1)

        self.refresh_agents()

    def refresh_agents(self) -> None:
        self.agent_list.clear()
        for name in detect_agents(self.project_root):
            self.agent_list.addItem(QListWidgetItem(name))
        if self.agent_list.count() == 0:
            self.agent_list.addItem(QListWidgetItem("No agent definitions found in this project."))

    def run_command(self, command: str) -> None:
        result = run_mediator_command(self.project_root, command)
        self.output.setPlainText(f"Project: {self.project_root}\n\nCommand: {command}\n\nResult:\n{result}")
        self.refresh_agents()

    def run_custom_command(self) -> None:
        command, ok = QInputDialog.getText(self, "Custom Mediator Command", "Enter command:")
        if ok and command.strip():
            self.run_command(command.strip())


class MediatorDesktopWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.projects: list[str] = load_projects()
        self.arch_window: ArchitectureWindow | None = None
        self.actions_window: ActionsWindow | None = None

        self.setWindowTitle("Mediator Desktop - Multi Project")
        self.resize(900, 640)

        root_layout = QVBoxLayout()
        self.setLayout(root_layout)

        header = QLabel(
            "Open any project folder. Then launch Architecture and Agents windows for that project."
        )
        header.setWordWrap(True)
        header.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        root_layout.addWidget(header)

        self.project_list = QListWidget()
        root_layout.addWidget(self.project_list, 1)

        button_row = QHBoxLayout()
        root_layout.addLayout(button_row)

        add_btn = QPushButton("Add Project Folder")
        add_btn.clicked.connect(self.add_project)
        button_row.addWidget(add_btn)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.remove_selected_project)
        button_row.addWidget(remove_btn)

        open_arch_btn = QPushButton("Open Architecture Window")
        open_arch_btn.clicked.connect(self.open_architecture_window)
        button_row.addWidget(open_arch_btn)

        open_actions_btn = QPushButton("Open Agents and Actions Window")
        open_actions_btn.clicked.connect(self.open_actions_window)
        button_row.addWidget(open_actions_btn)

        self.status = QLabel("")
        root_layout.addWidget(self.status)

        self.refresh_project_list()

    def refresh_project_list(self) -> None:
        self.project_list.clear()
        for project in self.projects:
            self.project_list.addItem(QListWidgetItem(project))

        if self.projects:
            self.status.setText(f"Saved projects: {len(self.projects)}")
        else:
            self.status.setText("No projects saved yet.")

    def selected_project_root(self) -> Path | None:
        current = self.project_list.currentItem()
        if current is None:
            QMessageBox.information(self, "Select a project", "Please select a project first.")
            return None
        return Path(current.text())

    def add_project(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose project folder")
        if not folder:
            return

        resolved = str(Path(folder).resolve())
        if resolved not in self.projects:
            self.projects.append(resolved)
            save_projects(self.projects)
            self.refresh_project_list()
        else:
            QMessageBox.information(self, "Already added", "That project is already in the list.")

    def remove_selected_project(self) -> None:
        current = self.project_list.currentItem()
        if current is None:
            QMessageBox.information(self, "Nothing selected", "Select a project to remove.")
            return

        value = current.text()
        self.projects = [item for item in self.projects if item != value]
        save_projects(self.projects)
        self.refresh_project_list()

    def open_architecture_window(self) -> None:
        project_root = self.selected_project_root()
        if project_root is None:
            return

        if not project_root.exists():
            QMessageBox.warning(self, "Missing folder", f"Project folder not found: {project_root}")
            return

        self.arch_window = ArchitectureWindow(project_root)
        self.arch_window.show()

    def open_actions_window(self) -> None:
        project_root = self.selected_project_root()
        if project_root is None:
            return

        if not project_root.exists():
            QMessageBox.warning(self, "Missing folder", f"Project folder not found: {project_root}")
            return

        self.actions_window = ActionsWindow(project_root)
        self.actions_window.show()


def main() -> int:
    app = QApplication(sys.argv)
    window = MediatorDesktopWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
