#!/usr/bin/env python3
"""Sync agent definitions for the two-layer agent architecture.

Source of truth: my-ai-framework/agents/*.agent.md
Interface wrappers: .github/agents/*.agent.md
Optional external sidecars: my-ai-framework/agents/<AgentName>/{agent.json,tools.json,prompt.md}

Directions:
- framework-to-github: generate wrapper .agent.md files from framework .agent.md files
- github-to-framework: validate wrapper entry references and report status
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def split_frontmatter(content: str) -> tuple[dict[str, object], str]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("Missing YAML frontmatter start '---'.")

    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break

    if end is None:
        raise ValueError("Missing YAML frontmatter end '---'.")

    frontmatter_lines = lines[1:end]
    body = "\n".join(lines[end + 1 :]).lstrip("\n")

    data: dict[str, object] = {}
    for raw in frontmatter_lines:
        line = raw.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        if key == "tools":
            list_value = value.strip()
            if list_value.startswith("[") and list_value.endswith("]"):
                inner = list_value[1:-1].strip()
                data[key] = [v.strip() for v in inner.split(",") if v.strip()]
            else:
                data[key] = []
        elif key == "user-invocable":
            data[key] = value.lower() == "true"
        else:
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]
            data[key] = value

    return data, body


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def sync_framework_to_github(repo_root: Path) -> int:
    github_dir = repo_root / ".github" / "agents"
    framework_dir = repo_root / "my-ai-framework" / "agents"
    github_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for framework_md in sorted(framework_dir.glob("*.agent.md")):
        meta, _body = split_frontmatter(framework_md.read_text(encoding="utf-8"))
        name = str(meta.get("name", framework_md.stem.replace(".agent", ""))).strip()
        if not name:
            continue
        description = str(meta.get("description", f"Wrapper for {name}")).strip()
        argument_hint = str(meta.get("argument-hint", "")).strip()
        user_invocable = bool(meta.get("user-invocable", True))
        tools = meta.get("tools", [])
        if not isinstance(tools, list):
            tools = []
        if name == "MediatorAI":
            tools = ["execute"]
        tools_text = ", ".join(str(t) for t in tools)

        body = (
            f"You are the VS Code {name} wrapper.\n\n"
            "Role:\n"
            "- Receive user commands from the VS Code sidebar.\n"
            "- Forward execution to the framework definition referenced by `entry`.\n"
            "- Return framework results back to the user.\n"
        )
        if name == "MediatorAI":
            body += (
                "- For local runtime routing, execute: `python ./.github/agents/mediator_bridge.py \"<task>\"`.\n"
            )

        wrapper = (
            "---\n"
            f'name: "{name}"\n'
            f'description: "{description}"\n'
            f'argument-hint: "{argument_hint}"\n'
            f'entry: "../../my-ai-framework/agents/{name}.agent.md"\n'
            f"tools: [{tools_text}]\n"
            f"user-invocable: {'true' if user_invocable else 'false'}\n"
            "---\n\n"
            f"{body}"
        )

        target_md = github_dir / f"{name}.agent.md"
        target_md.write_text(wrapper, encoding="utf-8")
        count += 1

    return count


def validate_github_wrappers(repo_root: Path) -> int:
    github_dir = repo_root / ".github" / "agents"
    validated = 0

    for wrapper_md in sorted(github_dir.glob("*.agent.md")):
        meta, _body = split_frontmatter(wrapper_md.read_text(encoding="utf-8"))
        entry = str(meta.get("entry", "")).strip()
        name = str(meta.get("name", wrapper_md.stem.replace(".agent", ""))).strip()

        if not entry:
            print(f"WARN: Missing entry in wrapper: {wrapper_md}")
            continue

        entry_path = (wrapper_md.parent / entry).resolve()
        if not entry_path.exists():
            print(f"WARN: Missing framework target for {name}: {entry_path}")
            continue
        validated += 1

    return validated


def generate_json_sidecars(repo_root: Path) -> int:
    """Generate folder-based agent.json/tools.json/prompt.md from framework .agent.md files."""
    framework_dir = repo_root / "my-ai-framework" / "agents"
    generated = 0

    for framework_md in sorted(framework_dir.glob("*.agent.md")):
        meta, body = split_frontmatter(framework_md.read_text(encoding="utf-8"))
        name = str(meta.get("name", framework_md.stem.replace(".agent", ""))).strip()
        if not name:
            continue

        target_dir = framework_dir / name
        target_dir.mkdir(parents=True, exist_ok=True)

        agent_json = {
            "name": name,
            "description": str(meta.get("description", "")),
            "argumentHint": str(meta.get("argument-hint", "")),
            "userInvocable": bool(meta.get("user-invocable", False)),
            "toolsFile": "./tools.json",
            "promptFile": "./prompt.md",
        }
        tools = meta.get("tools", [])
        if not isinstance(tools, list):
            tools = []
        tools_json = {"allowed": tools}

        write_json(target_dir / "agent.json", agent_json)
        write_json(target_dir / "tools.json", tools_json)
        (target_dir / "prompt.md").write_text(body.rstrip() + "\n", encoding="utf-8")
        generated += 1

    return generated


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync custom agent definitions between two formats.")
    parser.add_argument(
        "--direction",
        required=True,
        choices=["github-to-framework", "framework-to-github"],
        help="Sync direction.",
    )
    parser.add_argument(
        "--include-json",
        action="store_true",
        help="Also sync folder-based agent.json and tools.json sidecar files when present.",
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parent.parent),
        help="Repository root path. Defaults to this script's parent directory.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if args.direction == "framework-to-github":
        count = sync_framework_to_github(repo_root)
    else:
        count = validate_github_wrappers(repo_root)

    print(f"Synced {count} agent(s) using direction: {args.direction}")
    if args.include_json:
        json_count = generate_json_sidecars(repo_root)
        print(f"Generated {json_count} sidecar JSON set(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
