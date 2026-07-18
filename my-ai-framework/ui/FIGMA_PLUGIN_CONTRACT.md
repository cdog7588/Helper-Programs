# Figma Plugin Contract (Mediator)

This document defines the contract file exported by the live Mediator Figma window.

## Contract Location

The desktop app exports this file per project:

- `.mediator/figma_plugin_contract.json`

## Purpose

A Figma plugin can read this file and apply updates to Figma text layers and widgets, enabling native in-file updates instead of static screenshots.

## Schema (v1)

```json
{
  "schemaVersion": "1.0.0",
  "generatedAt": "2026-07-18T21:30:00",
  "project": {
    "name": "fitnessapp",
    "root": "C:/dev/fitness-intelligence-backend/fitnessapp"
  },
  "figma": {
    "fileKey": "<figma-file-key>",
    "nodeGroups": {
      "metaTabs": ["meta_backend"],
      "panels": ["panel_backend_layers"],
      "buttons": ["btn_figma_push"],
      "cards": [],
      "status": [],
      "inputs": [],
      "logs": []
    }
  },
  "bindings": {
    "btn_agent_send": "broadcast agent status check",
    "btn_service_connect": "ping all services",
    "btn_figma_pull": "refresh design from figma",
    "btn_figma_push": "push backend snapshot to figma"
  },
  "backendSummary": "...",
  "backendArchitecture": { "service": {} },
  "activityFeed": ["..."]
}
```

## Plugin Responsibilities

1. Parse `.mediator/figma_plugin_contract.json`.
2. Resolve target layers by naming convention (e.g. `panel_backend_layers`, `log_activity_feed`).
3. Populate text fields from:
   - `backendSummary`
   - `backendArchitecture`
   - `activityFeed`
4. Keep immutable naming contract prefixes (`panel_`, `btn_`, `status_`, etc.).

## Suggested Text Layer Mapping

- `panel_backend_layers` <- backend summary and architecture counters
- `panel_dashboard_activity_feed` <- activityFeed entries
- `log_sync_events` <- latest sync events

## Closed-Loop Flow

1. Figma renamed layers -> Mediator loader sync
2. Mediator backend scan -> contract export
3. Plugin consumes contract -> updates Figma layers
4. User edits in Figma -> reload in Mediator
