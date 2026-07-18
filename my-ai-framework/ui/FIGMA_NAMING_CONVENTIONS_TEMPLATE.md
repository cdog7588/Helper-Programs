# Figma Naming Conventions Template

Use this as the content for a dedicated Figma page named `Naming Conventions`.

## Purpose

This page is the source of truth for naming contracts used by the Mediator loader.
It keeps Figma AI, UI builders, and backend sync rules aligned.

## Prefix Contract

| Prefix | Meaning | Examples |
|---|---|---|
| `meta_` or `tab_` | Top-level navigation or mode tabs | `meta_backend`, `meta_agents`, `tab_monitoring` |
| `panel_` | Main dashboard sections | `panel_project_list`, `panel_backend_layers`, `panel_dashboard_activity_feed` |
| `btn_` | Action button nodes | `btn_agent_send`, `btn_service_connect`, `btn_figma_pull`, `btn_figma_push` |
| `card_` | Compact summary cards | `card_service_health`, `card_project_status` |
| `status_` | Real-time status widgets | `status_agent_analyzer`, `status_service_api` |
| `input_` | Editable input controls | `input_project_filter`, `input_custom_command` |
| `log_` | Feed and log display regions | `log_activity_feed`, `log_sync_events` |

## Required Nodes

- `panel_project_list`
- `panel_backend_layers`
- `panel_agents`
- `panel_actions`
- `panel_dashboard_activity_feed`
- `btn_agent_send`
- `btn_service_connect`
- `btn_figma_pull`
- `btn_figma_push`

## Hidden Metadata Layers

Create text layers on this page and set them to hidden:

- `meta_sync_version: v1`
- `meta_loader_target: mediator_gui.py`
- `meta_contract_owner: MediatorAI`
- `meta_last_reviewed: YYYY-MM-DD`

## Notes

- Keep node names stable once automation is connected.
- Use duplicate + rename for new projects rather than editing existing contract names.
- If a button requires a new command, add the `btn_` name first, then map it in code.
