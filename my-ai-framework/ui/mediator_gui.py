#!/usr/bin/env python3
"""Multi-project Mediator desktop UI (PySide6) with live Figma support."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from PySide6.QtCore import QTimer, Qt
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
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from figma_config import get_figma_file_key, get_figma_token  # type: ignore
else:
    from .figma_config import get_figma_file_key, get_figma_token

APP_STATE_DIR = Path.home() / ".mediator_desktop"
PROJECTS_FILE = APP_STATE_DIR / "projects.json"
FIGMA_SYNC_LOG = APP_STATE_DIR / "figma_sync.log"
PLUGIN_CONTRACT_REL_PATH = Path(".mediator") / "figma_plugin_contract.json"

FIGMA_META_TABS: list[str] = []
FIGMA_PANELS: list[str] = []
FIGMA_BUTTONS: list[str] = []
FIGMA_CARDS: list[str] = []
FIGMA_STATUS: list[str] = []
FIGMA_INPUTS: list[str] = []
FIGMA_LOGS: list[str] = []

IGNORE_DIR_NAMES = {
    ".git",
    ".idea",
    ".vscode",
    "node_modules",
    "dist",
    "build",
    "out",
    "target",
    "venv",
    ".venv",
    "env",
    "__pycache__",
}

SPRING_ENDPOINT_PATTERN = re.compile(
    r"@(?P<anno>GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)\s*\(\s*\"(?P<path>[^\"]+)\""
)


def load_projects() -> list[str]:
    if not PROJECTS_FILE.exists():
        return []
    try:
        data = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            projects = [str(Path(item).resolve()) for item in data if isinstance(item, str)]
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


def _extract_controller_endpoints(file_path: Path) -> list[dict[str, str]]:
    endpoints: list[dict[str, str]] = []
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return endpoints

    for match in SPRING_ENDPOINT_PATTERN.finditer(text):
        anno = match.group("anno")
        endpoint_path = match.group("path")
        method = anno.replace("Mapping", "").upper()
        endpoints.append({"method": method, "path": endpoint_path, "returns": "Object"})
    return endpoints


def _discover_backend_architecture(project_root: Path) -> dict[str, Any]:
    controllers: list[dict[str, Any]] = []
    services: list[dict[str, Any]] = []
    repositories: list[dict[str, Any]] = []
    dtos: list[dict[str, Any]] = []

    for file_path in project_root.rglob("*"):
        if not file_path.is_file():
            continue
        if any(part in IGNORE_DIR_NAMES for part in file_path.parts):
            continue
        if file_path.suffix.lower() not in {".java", ".kt", ".py", ".ts", ".js"}:
            continue

        stem = file_path.stem
        lowered = stem.lower()

        if lowered.endswith("controller"):
            controllers.append(
                {
                    "name": stem,
                    "endpoints": _extract_controller_endpoints(file_path),
                    "source": str(file_path.relative_to(project_root)),
                }
            )
        elif lowered.endswith("service"):
            services.append(
                {
                    "name": stem,
                    "methods": [],
                    "source": str(file_path.relative_to(project_root)),
                }
            )
        elif lowered.endswith("repository"):
            repositories.append(
                {
                    "name": stem,
                    "entity": "UnknownEntity",
                    "source": str(file_path.relative_to(project_root)),
                }
            )
        elif lowered.endswith("dto") or lowered.endswith("model") or lowered.endswith("entity"):
            dtos.append(
                {
                    "name": stem,
                    "fields": {},
                    "source": str(file_path.relative_to(project_root)),
                }
            )

    return {
        "service": {
            "name": project_root.name,
            "controllers": sorted(controllers, key=lambda item: item["name"]),
            "services": sorted(services, key=lambda item: item["name"]),
            "repositories": sorted(repositories, key=lambda item: item["name"]),
            "dtos": sorted(dtos, key=lambda item: item["name"]),
        },
        "meta": {
            "generatedBy": "WorkspaceAnalyzer",
            "mode": "fallback-scan",
            "projectRoot": str(project_root),
        },
    }


def parse_architecture(project_root: Path) -> tuple[str, str]:
    arch_path = project_root / "architecture-generator" / "architecture.json"
    used_fallback = False

    if arch_path.exists():
        try:
            data: dict[str, Any] = json.loads(arch_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = _discover_backend_architecture(project_root)
            used_fallback = True
    else:
        data = _discover_backend_architecture(project_root)
        used_fallback = True

    service = data.get("service", {}) if isinstance(data, dict) else {}
    controllers = service.get("controllers", []) if isinstance(service, dict) else []
    services = service.get("services", []) if isinstance(service, dict) else []
    repositories = service.get("repositories", []) if isinstance(service, dict) else []
    dtos = service.get("dtos", []) if isinstance(service, dict) else []

    summary_lines = [
        "Backend Architecture Summary",
        "============================",
        f"Project: {project_root}",
        f"mode: {'WorkspaceAnalyzer fallback scan' if used_fallback else 'architecture.json'}",
        "",
        f"controllers: {len(controllers)}",
        f"services: {len(services)}",
        f"repositories: {len(repositories)}",
        f"dtos/models/entities: {len(dtos)}",
    ]

    if used_fallback:
        summary_lines.append(
            "\nNo architecture-generator/architecture.json was found, so WorkspaceAnalyzer inferred structure from source files."
        )

    pretty_json = json.dumps(data, indent=2)
    return "\n".join(summary_lines), pretty_json


def detect_agents(project_root: Path) -> list[str]:
    agents: set[str] = {"WorkspaceAnalyzer"}
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
            "Analyzer windows still work, but command execution requires mediator runtime files in that project."
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


def fetch_figma_file() -> dict[str, Any]:
    token = get_figma_token()
    file_key = get_figma_file_key()
    if not token or not file_key:
        raise RuntimeError("Missing FIGMA_TOKEN or FIGMA_FILE_KEY environment variable.")

    url = f"https://api.figma.com/v1/files/{file_key}"
    response = requests.get(url, headers={"X-Figma-Token": token}, timeout=20)
    response.raise_for_status()
    return response.json()


def figma_named_nodes(figma_json: dict[str, Any]) -> dict[str, dict[str, Any]]:
    named: dict[str, dict[str, Any]] = {}

    def walk(node: dict[str, Any]) -> None:
        name = node.get("name")
        if isinstance(name, str) and name:
            named[name] = node
        children = node.get("children")
        if isinstance(children, list):
            for child in children:
                if isinstance(child, dict):
                    walk(child)

    document = figma_json.get("document")
    if isinstance(document, dict):
        walk(document)
    return named


def categorize_named_nodes(named_nodes: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    groups = {
        "meta_tabs": [],
        "panels": [],
        "buttons": [],
        "cards": [],
        "status": [],
        "inputs": [],
        "logs": [],
    }

    for name in sorted(named_nodes.keys()):
        lowered = name.lower()
        if lowered.startswith("meta_") or lowered.startswith("tab_"):
            groups["meta_tabs"].append(name)
        if lowered.startswith("panel_"):
            groups["panels"].append(name)
        if lowered.startswith("btn_"):
            groups["buttons"].append(name)
        if lowered.startswith("card_"):
            groups["cards"].append(name)
        if lowered.startswith("status_"):
            groups["status"].append(name)
        if lowered.startswith("input_"):
            groups["inputs"].append(name)
        if lowered.startswith("log_"):
            groups["logs"].append(name)

    return groups


def update_figma_constants(groups: dict[str, list[str]]) -> None:
    global FIGMA_META_TABS, FIGMA_PANELS, FIGMA_BUTTONS, FIGMA_CARDS, FIGMA_STATUS, FIGMA_INPUTS, FIGMA_LOGS
    FIGMA_META_TABS = groups["meta_tabs"]
    FIGMA_PANELS = groups["panels"]
    FIGMA_BUTTONS = groups["buttons"]
    FIGMA_CARDS = groups["cards"]
    FIGMA_STATUS = groups["status"]
    FIGMA_INPUTS = groups["inputs"]
    FIGMA_LOGS = groups["logs"]


def append_figma_sync_log(message: str) -> None:
    APP_STATE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().isoformat(timespec="seconds")
    with FIGMA_SYNC_LOG.open("a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}] {message}\n")


def post_figma_comment(message: str, node_id: str | None = None) -> str:
    token = get_figma_token()
    file_key = get_figma_file_key()
    if not token or not file_key:
        return "Missing FIGMA_TOKEN or FIGMA_FILE_KEY environment variable."

    url = f"https://api.figma.com/v1/files/{file_key}/comments"
    payload: dict[str, Any] = {"message": message}
    if node_id:
        payload["client_meta"] = {"node_id": node_id}

    response = requests.post(url, headers={"X-Figma-Token": token}, json=payload, timeout=20)
    if response.status_code >= 400:
        return f"Figma comment push failed ({response.status_code}): {response.text[:240]}"
    return "Figma comment push succeeded."


def project_contract_path(project_root: Path) -> Path:
    return project_root / PLUGIN_CONTRACT_REL_PATH


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
        root_layout.addWidget(QLabel("Architecture JSON (file or analyzed fallback)"))
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

    def run_command(self, command: str) -> None:
        result = run_mediator_command(self.project_root, command)
        self.output.setPlainText(f"Project: {self.project_root}\n\nCommand: {command}\n\nResult:\n{result}")
        self.refresh_agents()

    def run_custom_command(self) -> None:
        command, ok = QInputDialog.getText(self, "Custom Mediator Command", "Enter command:")
        if ok and command.strip():
            self.run_command(command.strip())


class LiveFigmaWindow(QWidget):
    def __init__(self, project_root: Path) -> None:
        super().__init__()
        self.project_root = project_root
        self.named_nodes: dict[str, dict[str, Any]] = {}
        self.grouped_nodes: dict[str, list[str]] = {}

        self.setWindowTitle(f"Live Figma - {project_root.name}")
        self.resize(1260, 860)
        self.setStyleSheet(
            """
            QWidget { background: #0d1117; color: #d7dde8; }
            QGroupBox {
                border: 1px solid #2a3445;
                border-radius: 8px;
                margin-top: 10px;
                font-weight: 600;
                color: #a7d3ff;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
            QPushButton {
                background: #152033;
                border: 1px solid #2c3f5f;
                border-radius: 6px;
                padding: 6px 10px;
            }
            QPushButton:hover { background: #1b2a45; }
            QTextEdit, QListWidget, QScrollArea {
                background: #0f1624;
                border: 1px solid #253147;
                border-radius: 6px;
            }
            """
        )

        root_layout = QVBoxLayout()
        self.setLayout(root_layout)

        top_row = QHBoxLayout()
        root_layout.addLayout(top_row)

        refresh_btn = QPushButton("Refresh from Figma")
        refresh_btn.clicked.connect(self.reload_from_figma)
        top_row.addWidget(refresh_btn)

        push_btn = QPushButton("Push Backend Snapshot to Figma")
        push_btn.clicked.connect(self.push_backend_snapshot_to_figma)
        top_row.addWidget(push_btn)

        export_btn = QPushButton("Export Plugin Contract")
        export_btn.clicked.connect(self.export_plugin_contract)
        top_row.addWidget(export_btn)

        copy_contract_btn = QPushButton("Copy Naming Contract")
        copy_contract_btn.clicked.connect(self.copy_naming_contract)
        top_row.addWidget(copy_contract_btn)

        self.auto_btn = QPushButton("Enable Auto Refresh (20s)")
        self.auto_btn.clicked.connect(self.toggle_auto_refresh)
        top_row.addWidget(self.auto_btn)

        top_row.addStretch(1)

        self.info = QLabel("Waiting for Figma load...")
        root_layout.addWidget(self.info)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        root_layout.addWidget(self.scroll, 1)

        self.dynamic_root = QWidget()
        self.dynamic_layout = QVBoxLayout()
        self.dynamic_root.setLayout(self.dynamic_layout)
        self.scroll.setWidget(self.dynamic_root)

        self.activity_feed = QTextEdit()
        self.activity_feed.setReadOnly(True)
        root_layout.addWidget(self.activity_feed, 1)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        root_layout.addWidget(self.output, 1)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(20_000)
        self.refresh_timer.timeout.connect(self.reload_from_figma)

        self.reload_from_figma()

    def add_activity(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}"
        existing = self.activity_feed.toPlainText().strip()
        self.activity_feed.setPlainText((existing + "\n" + line).strip())
        append_figma_sync_log(f"{self.project_root.name}: {message}")

    def clear_dynamic_layout(self) -> None:
        while self.dynamic_layout.count() > 0:
            item = self.dynamic_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def command_for_button_name(self, name: str) -> str | None:
        key = name.lower()
        if key == "btn_agent_send":
            return "__agent_send__"
        if key == "btn_service_connect":
            return "__service_connect__"
        if key == "btn_figma_pull":
            return "__figma_pull__"
        if key == "btn_figma_push":
            return "__figma_push__"
        if "analy" in key:
            return "analyze backend architecture"
        if "sync" in key:
            return "sync architecture"
        if "deploy" in key:
            return "deploy"
        if "audit" in key:
            return "audit"
        if "valid" in key:
            return "validate architecture"
        return None

    def build_from_nodes(self) -> None:
        self.clear_dynamic_layout()

        panel_names = self.grouped_nodes["panels"]
        button_names = self.grouped_nodes["buttons"]
        meta_tabs = self.grouped_nodes["meta_tabs"]
        cards = self.grouped_nodes["cards"]
        status_nodes = self.grouped_nodes["status"]
        input_nodes = self.grouped_nodes["inputs"]
        log_nodes = self.grouped_nodes["logs"]

        if not panel_names and not button_names:
            self.dynamic_layout.addWidget(
                QLabel("No panel_/btn_ named layers found. Add those names in Figma to drive UI structure.")
            )
            self.dynamic_layout.addStretch(1)
            return

        if meta_tabs:
            tabs_box = QGroupBox("Meta Tabs")
            tabs_layout = QHBoxLayout()
            tabs_box.setLayout(tabs_layout)
            for tab_name in meta_tabs:
                pill = QLabel(tab_name)
                pill.setStyleSheet("padding:4px 8px; border:1px solid #33445f; border-radius:12px;")
                tabs_layout.addWidget(pill)
            tabs_layout.addStretch(1)
            self.dynamic_layout.addWidget(tabs_box)

        for panel_name in panel_names:
            group = QGroupBox(panel_name.replace("panel_", "").replace("_", " ").title())
            group_layout = QVBoxLayout()
            group.setLayout(group_layout)

            group_layout.addWidget(QLabel(f"Source node: {panel_name}"))

            # Place matching buttons inside the panel by prefix convention, e.g. panel_agents + btn_agents_sync
            panel_key = panel_name.lower().replace("panel_", "")
            linked = [name for name in button_names if panel_key in name.lower()]
            for button_name in linked:
                self._add_dynamic_button(group_layout, button_name)

            self.dynamic_layout.addWidget(group)

        panel_keys = [p.lower().replace("panel_", "") for p in panel_names]
        unassigned = [name for name in button_names if not any(key and key in name.lower() for key in panel_keys)]
        if unassigned:
            group = QGroupBox("Actions")
            group_layout = QVBoxLayout()
            group.setLayout(group_layout)
            for button_name in unassigned:
                self._add_dynamic_button(group_layout, button_name)
            self.dynamic_layout.addWidget(group)

        if cards:
            card_box = QGroupBox("Cards")
            card_layout = QVBoxLayout()
            card_box.setLayout(card_layout)
            for name in cards:
                card_layout.addWidget(QLabel(f"card: {name}"))
            self.dynamic_layout.addWidget(card_box)

        if status_nodes:
            status_box = QGroupBox("Status Widgets")
            status_layout = QVBoxLayout()
            status_box.setLayout(status_layout)
            for name in status_nodes:
                status_layout.addWidget(QLabel(f"status: {name}"))
            self.dynamic_layout.addWidget(status_box)

        if input_nodes:
            input_box = QGroupBox("Inputs")
            input_layout = QVBoxLayout()
            input_box.setLayout(input_layout)
            for name in input_nodes:
                input_layout.addWidget(QLabel(f"input: {name}"))
            self.dynamic_layout.addWidget(input_box)

        if log_nodes:
            log_box = QGroupBox("Log Widgets")
            log_layout = QVBoxLayout()
            log_box.setLayout(log_layout)
            for name in log_nodes:
                log_layout.addWidget(QLabel(f"log: {name}"))
            self.dynamic_layout.addWidget(log_box)

        self.dynamic_layout.addStretch(1)

    def _add_dynamic_button(self, layout: QVBoxLayout, button_name: str) -> None:
        button_text = button_name.replace("btn_", "").replace("_", " ").title()
        button = QPushButton(button_text)
        command = self.command_for_button_name(button_name)
        if command is None:
            button.clicked.connect(
                lambda _checked=False, n=button_name: self.output.setPlainText(
                    f"No command mapping for {n}.\nUse btn_agent_send, btn_service_connect, btn_figma_pull, btn_figma_push, or extend mapping."
                )
            )
        else:
            button.clicked.connect(lambda _checked=False, c=command: self.run_command(c))
        layout.addWidget(button)

    def run_command(self, command: str) -> None:
        if command == "__agent_send__":
            agents = ", ".join(detect_agents(self.project_root))
            result = f"Broadcast agent status check simulated. Agents detected: {agents}"
            self.output.setPlainText(result)
            self.add_activity("Executed btn_agent_send (status broadcast)")
            return

        if command == "__service_connect__":
            result = run_mediator_command(self.project_root, "monitor services health")
            self.output.setPlainText(result)
            self.add_activity("Executed btn_service_connect (service ping)")
            return

        if command == "__figma_pull__":
            self.reload_from_figma()
            self.add_activity("Executed btn_figma_pull (design refresh)")
            return

        if command == "__figma_push__":
            self.export_plugin_contract()
            self.push_backend_snapshot_to_figma()
            self.add_activity("Executed btn_figma_push (backend snapshot push)")
            return

        result = run_mediator_command(self.project_root, command)
        self.output.setPlainText(f"Project: {self.project_root}\nCommand: {command}\n\n{result}")
        self.add_activity(f"Executed mediator command: {command}")

    def push_backend_snapshot_to_figma(self) -> None:
        summary, raw_json = parse_architecture(self.project_root)
        trimmed_json = raw_json[:3000]
        message = (
            "Mediator backend sync update\n"
            f"Project: {self.project_root.name}\n\n"
            f"{summary}\n\n"
            "JSON snippet:\n"
            f"{trimmed_json}"
        )

        target_node_id: str | None = None
        panel = self.named_nodes.get("panel_backend_layers")
        if isinstance(panel, dict):
            node_id = panel.get("id")
            if isinstance(node_id, str):
                target_node_id = node_id

        result = post_figma_comment(message, target_node_id)
        self.output.setPlainText(result)
        self.add_activity(result)

    def build_plugin_contract(self) -> dict[str, Any]:
        summary, raw_json = parse_architecture(self.project_root)
        try:
            backend_json = json.loads(raw_json)
        except json.JSONDecodeError:
            backend_json = {"raw": raw_json}

        contract = {
            "schemaVersion": "1.0.0",
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
            "project": {
                "name": self.project_root.name,
                "root": str(self.project_root),
            },
            "figma": {
                "fileKey": get_figma_file_key(),
                "nodeGroups": {
                    "metaTabs": FIGMA_META_TABS,
                    "panels": FIGMA_PANELS,
                    "buttons": FIGMA_BUTTONS,
                    "cards": FIGMA_CARDS,
                    "status": FIGMA_STATUS,
                    "inputs": FIGMA_INPUTS,
                    "logs": FIGMA_LOGS,
                },
            },
            "bindings": {
                "btn_agent_send": "broadcast agent status check",
                "btn_service_connect": "ping all services",
                "btn_figma_pull": "refresh design from figma",
                "btn_figma_push": "push backend snapshot to figma",
            },
            "backendSummary": summary,
            "backendArchitecture": backend_json,
            "activityFeed": [
                line.strip()
                for line in self.activity_feed.toPlainText().splitlines()
                if line.strip()
            ][-200:],
        }
        return contract

    def export_plugin_contract(self) -> Path:
        contract = self.build_plugin_contract()
        destination = project_contract_path(self.project_root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(contract, indent=2), encoding="utf-8")
        self.add_activity(f"Exported plugin contract: {destination}")
        self.output.setPlainText(f"Plugin contract exported to:\n{destination}")
        return destination

    def copy_naming_contract(self) -> None:
        contract = (
            "Naming Conventions\n"
            "meta_: top tabs\n"
            "panel_: layout sections\n"
            "btn_: command buttons\n"
            "card_: compact info cards\n"
            "status_: live status widgets\n"
            "input_: user inputs\n"
            "log_: log or feed layers\n"
            "\n"
            "Recommended names:\n"
            "meta_backend, meta_agents, meta_monitoring\n"
            "panel_project_list, panel_backend_layers, panel_dashboard_activity_feed\n"
            "btn_agent_send, btn_service_connect, btn_figma_pull, btn_figma_push\n"
        )
        QApplication.clipboard().setText(contract)
        self.add_activity("Copied naming contract to clipboard")

    def reload_from_figma(self) -> None:
        try:
            figma_json = fetch_figma_file()
            self.named_nodes = figma_named_nodes(figma_json)
            self.grouped_nodes = categorize_named_nodes(self.named_nodes)
            update_figma_constants(self.grouped_nodes)

            counts = (
                f"tabs={len(FIGMA_META_TABS)}, panels={len(FIGMA_PANELS)}, "
                f"buttons={len(FIGMA_BUTTONS)}, cards={len(FIGMA_CARDS)}, "
                f"status={len(FIGMA_STATUS)}, inputs={len(FIGMA_INPUTS)}, logs={len(FIGMA_LOGS)}"
            )
            self.info.setText(
                f"Loaded {len(self.named_nodes)} named Figma nodes for {self.project_root.name}. {counts}"
            )
            self.add_activity(f"Figma sync completed: {counts}")
            self.build_from_nodes()
        except Exception as exc:  # noqa: BLE001
            self.info.setText("Figma load failed.")
            self.output.setPlainText(
                "Could not fetch live Figma file.\n"
                f"Reason: {exc}\n\n"
                "Set FIGMA_TOKEN and FIGMA_FILE_KEY environment variables and retry."
            )
            self.add_activity(f"Figma sync failed: {exc}")

    def toggle_auto_refresh(self) -> None:
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()
            self.auto_btn.setText("Enable Auto Refresh (20s)")
        else:
            self.refresh_timer.start()
            self.auto_btn.setText("Disable Auto Refresh")


class MediatorDesktopWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.projects: list[str] = load_projects()
        self.arch_window: ArchitectureWindow | None = None
        self.actions_window: ActionsWindow | None = None
        self.figma_window: LiveFigmaWindow | None = None

        self.setWindowTitle("Mediator Desktop - Multi Project")
        self.resize(920, 680)

        root_layout = QVBoxLayout()
        self.setLayout(root_layout)

        header = QLabel(
            "Select a project and open: Architecture, Agents/Actions, or Live Figma (dynamic UI)."
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

        open_figma_btn = QPushButton("Open Live Figma Window")
        open_figma_btn.clicked.connect(self.open_figma_window)
        button_row.addWidget(open_figma_btn)

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

    def open_figma_window(self) -> None:
        project_root = self.selected_project_root()
        if project_root is None:
            return
        if not project_root.exists():
            QMessageBox.warning(self, "Missing folder", f"Project folder not found: {project_root}")
            return

        self.figma_window = LiveFigmaWindow(project_root)
        self.figma_window.show()


def main() -> int:
    app = QApplication(sys.argv)
    window = MediatorDesktopWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
