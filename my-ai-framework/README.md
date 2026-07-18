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

## Live Figma Workflow

The desktop UI loader supports a naming-contract driven workflow for live Figma integration.

### Setup

1. Set environment variables locally:
	- `FIGMA_TOKEN`
	- `FIGMA_FILE_KEY`
2. In Figma, create a page named `Naming Conventions`.
3. Copy the naming contract from:
	- `my-ai-framework/ui/FIGMA_NAMING_CONVENTIONS_TEMPLATE.md`

### Loader Behavior

The live window in `my-ai-framework/ui/mediator_gui.py` reads named nodes by prefix:

- `meta_` / `tab_`
- `panel_`
- `btn_`
- `card_`
- `status_`
- `input_`
- `log_`

Detected nodes are grouped into constants:

- `FIGMA_META_TABS`
- `FIGMA_PANELS`
- `FIGMA_BUTTONS`
- `FIGMA_CARDS`
- `FIGMA_STATUS`
- `FIGMA_INPUTS`
- `FIGMA_LOGS`

Sync events are written to:

- `%USERPROFILE%/.mediator_desktop/figma_sync.log`

### Built-In Button Bindings

- `btn_agent_send` -> agent status broadcast action
- `btn_service_connect` -> service health command
- `btn_figma_pull` -> refresh design from Figma API
- `btn_figma_push` -> push backend architecture snapshot to Figma comments

### Closed Loop

The current implementation supports this cycle:

- Figma -> Mediator UI loader (pull and parse named nodes)
- Backend -> architecture summary/json extraction
- Mediator -> Figma (comment push with backend snapshot)

For full write-back into text layers, a Figma plugin or future write-capable API flow is required.