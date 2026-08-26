# install-kb.ps1 — One-click install of GSD Knowledge Base skills (Windows)
# Usage: .\scripts\install-kb.ps1 [-Mode copy|link] [-Target <dir>]

param(
    [ValidateSet("copy", "link")]
    [string]$Mode = "copy",
    [string]$Target = "$env:USERPROFILE\.claude\skills"
)

$ErrorActionPreference = "Stop"

# Source dirs resolve relative to THIS script (release boundary). Works from a
# release-only distribution (components at the repo root) or <repo>/release.
$ReleaseRoot = Split-Path -Parent $PSCommandPath
$SourceDir = Join-Path $ReleaseRoot "skills"
if (-not (Test-Path $SourceDir -PathType Container)) {
    # Legacy entry: scripts/install-kb.ps1 inside a full clone → sibling release/
    $RepoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
    $ReleaseRoot = Join-Path $RepoRoot "release"
    $SourceDir = Join-Path $ReleaseRoot "skills"
}

# Ensure target exists
if (-not (Test-Path $Target)) {
    New-Item -ItemType Directory -Path $Target -Force | Out-Null
}

# Find all kb skills
$KbSkills = Get-ChildItem -Path $SourceDir -Directory -Filter "gsd-kb-*" | Sort-Object Name
$Count = 0

Write-Host "GSD Knowledge Base Skills Installer" -ForegroundColor Cyan
Write-Host ("=" * 44)
Write-Host "Source:  $SourceDir"
Write-Host "Target:  $Target"
Write-Host "Mode:    $Mode"
Write-Host ("-" * 44)

foreach ($skill in $KbSkills) {
    $targetPath = Join-Path $Target $skill.Name

    # Remove existing
    if (Test-Path $targetPath) {
        Remove-Item -Recurse -Force $targetPath -Confirm:$false
    }

    if ($Mode -eq "link") {
        New-Item -ItemType SymbolicLink -Path $targetPath -Target $skill.FullName | Out-Null
        Write-Host "  [link] $($skill.Name)"
    } else {
        Copy-Item -Recurse -Path $skill.FullName -Destination $targetPath
        Write-Host "  [copy] $($skill.Name)"
    }
    $Count++
}

Write-Host ("-" * 44)
Write-Host "[OK] Installed $Count KB skills to $Target" -ForegroundColor Green
Write-Host ""

# Knowledge-base CLI
$KbCliSource = Join-Path $ReleaseRoot "knowledge-base"
$KbCliTarget = Join-Path $env:USERPROFILE ".claude\knowledge-base"

if (Test-Path (Join-Path $KbCliSource "packages\cli\__main__.py")) {
    if (-not (Test-Path $KbCliTarget)) {
        if ($Mode -eq "link") {
            New-Item -ItemType SymbolicLink -Path $KbCliTarget -Target $KbCliSource | Out-Null
            Write-Host "  [link] knowledge-base CLI -> $KbCliTarget"
        } else {
            Copy-Item -Recurse -Path $KbCliSource -Destination $KbCliTarget
            Write-Host "  [copy] knowledge-base CLI -> $KbCliTarget"
        }
    } else {
        Write-Host "  [skip] knowledge-base CLI already at $KbCliTarget"
    }
} else {
    Write-Host "  [warn] knowledge-base/packages/cli not found in repo" -ForegroundColor Yellow
    Write-Host "         Graph build and batch-fill will not work without it"
}

Write-Host ""
Write-Host "Done. Restart Claude Code to pick up new skills."
Write-Host "Available commands: /gsd-kb-init, /gsd-kb-fill, /gsd-kb-gen-tests, /gsd-kb-query"
