$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")

python (Join-Path $scriptDir "sync_agents.py") --direction framework-to-github --repo-root $repoRoot
