# Agent Layers

This project uses a two-layer agent setup.

## Sidebar Agents (`.github/agents`)

- Purpose: VS Code discovery and invocation.
- Files here are wrappers with metadata and an `entry` pointer.

Example:

```md
---
name: "MediatorAI"
description: "Routes tasks to framework agents."
entry: "../../my-ai-framework/agents/MediatorAI.agent.md"
user-invocable: true
---
```

## Framework Agents (`my-ai-framework/agents`)

- Purpose: full operational logic for external and internal automation.
- Files include complete frontmatter, tools, and instruction bodies.

## Current Agent Inventory

- MediatorAI
- GeneratorAgent
- AnalyzerAgent
- ArchitectureAgent
- SyncAgent
- FileManagerAgent
- ValidatorAgent
- DocumentationAgent
- TestAgent
- DeploymentAgent
- MonitorAgent
- CodeAuditAgent
- ResourceMonitorAgent

## Sync Helper

Use [sync_agents.py](sync_agents.py) in this folder to regenerate wrappers from framework agents.

Run from repository root:

```powershell
python ./.github/agents/sync_agents.py
```

This script updates `.github/agents/*.agent.md` wrappers using `my-ai-framework/agents/*.agent.md` as source of truth.

If wrapper and framework definitions diverge, regenerate wrappers from framework files.
