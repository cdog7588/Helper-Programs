# Agent Sync Workflow

This project uses a two-layer architecture:

- Framework logic source: `my-ai-framework/agents/*.agent.md`
- VS Code wrappers: `.github/agents/*.agent.md` (with `entry` pointers)
- Optional external sidecars: `my-ai-framework/agents/<AgentName>/{agent.json,tools.json,prompt.md}`

## Directories

- Framework source format: `my-ai-framework/agents/*.agent.md`
- Sidebar wrapper format: `.github/agents/*.agent.md`
- External sidecars: `my-ai-framework/agents/<AgentName>/`

## Sync Commands

Run from the repository root:

```powershell
./scripts/sync_github_to_framework.ps1
```

This validates wrapper `entry` references and reports coverage.

```powershell
./scripts/sync_framework_to_github.ps1
```

This regenerates `.github/agents` wrapper files from framework `.agent.md` files.

If script execution is restricted on Windows, run the Python command directly instead of `.ps1` wrappers.

You can also call the Python script directly:

```powershell
python ./scripts/sync_agents.py --direction framework-to-github
python ./scripts/sync_agents.py --direction github-to-framework
python ./scripts/sync_agents.py --direction framework-to-github --include-json
```

`--include-json` generates `agent.json`, `tools.json`, and `prompt.md` sidecars from framework `.agent.md` files.

## Recommended Source of Truth

- Prefer editing `my-ai-framework/agents/*.agent.md`.
- Run `sync_framework_to_github.ps1` after framework changes.
- Use `github-to-framework` as a validation pass for wrapper integrity.

## Notes

- Wrapper files are generated and may overwrite manual wrapper edits.
- Sidecar folders are generated from framework frontmatter and body.