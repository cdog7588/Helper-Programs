#!/usr/bin/env python3
"""Generate .github/agents wrapper files from my-ai-framework/agents logic files."""

from __future__ import annotations

from pathlib import Path


def parse_frontmatter(md: str) -> dict[str, object]:
    lines = md.splitlines()
    result: dict[str, object] = {}
    if not lines or lines[0].strip() != "---":
        return result

    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return result

    for raw in lines[1:end]:
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
                result[key] = [v.strip() for v in inner.split(",") if v.strip()]
            else:
                result[key] = []
        elif key == "user-invocable":
            result[key] = value.lower() == "true"
        else:
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]
            result[key] = value
    return result


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    wrappers_dir = repo_root / ".github" / "agents"
    framework_dir = repo_root / "my-ai-framework" / "agents"

    wrappers_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    for full_agent in sorted(framework_dir.glob("*.agent.md")):
        meta = parse_frontmatter(full_agent.read_text(encoding="utf-8"))
        name = str(meta.get("name", full_agent.stem.replace(".agent", ""))).strip()
        description = str(meta.get("description", f"Wrapper for {name}")).strip()
        argument_hint = str(meta.get("argument-hint", "")).strip()
        tools = meta.get("tools", [])
        if not isinstance(tools, list):
            tools = []
        if name == "MediatorAI":
            tools = ["execute"]
        tools_text = ", ".join(str(t) for t in tools)
        user_invocable = bool(meta.get("user-invocable", True))

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

        target = wrappers_dir / f"{name}.agent.md"
        target.write_text(wrapper, encoding="utf-8")
        count += 1

    print(f"Generated {count} wrapper agent file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
