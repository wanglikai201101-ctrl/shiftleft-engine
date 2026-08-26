---
name: gsd-kb-install
description: "One-click install/update of GSD Knowledge Base skills to user runtime"
argument-hint: "[--mode copy|link] [--target <dir>] [--uninstall]"
allowed-tools:
  - Read
  - Bash
  - Glob
---



<objective>
Install or update all gsd-kb-* skills from this project to the user's Claude Code runtime
directory (~/.claude/skills/), making KB commands immediately available.

Also installs the knowledge-base CLI (Python) needed for graph build and batch-fill.

Use cases:
- First-time setup: "I cloned gsd-core, now I want KB commands"
- Update after pull: "Skills changed upstream, sync to my runtime"
- Uninstall: "Remove all KB skills from my runtime"
</objective>

<process>

## Step 1: Parse arguments

Extract from `$ARGUMENTS`:
- `--mode <copy|link>` (optional, default: `copy`)
  - `copy`: full file copy — safe, no dependency on repo location
  - `link`: symlink — dev mode, changes in repo auto-reflect in runtime
- `--target <path>` (optional, default: `~/.claude/skills`)
- `--uninstall` (optional): remove all gsd-kb-* from target instead of installing

## Step 2: Detect environment

```bash
# Detect OS
OS=$(uname -s 2>/dev/null || echo "Windows")

# Locate repo root (where this skill lives)
REPO_ROOT="$(cd "$(dirname "$(find . -path '*/skills/gsd-kb-install/SKILL.md' -print -quit 2>/dev/null || echo .)")/../../.." && pwd)"
# Fallback: use known paths
if [ ! -d "$REPO_ROOT/skills/gsd-kb-fill" ]; then
  for candidate in \
    "$HOME/gsd-core" \
    "$(pwd)" \
    "$HOME/.claude/gsd-core"; do
    if [ -d "$candidate/skills/gsd-kb-fill" ]; then
      REPO_ROOT="$candidate"
      break
    fi
  done
fi

SOURCE_DIR="$REPO_ROOT/skills"
TARGET_DIR="${target:-$HOME/.claude/skills}"
```

Verify source exists:
```bash
ls "$SOURCE_DIR"/gsd-kb-* >/dev/null 2>&1 || { echo "❌ Cannot find KB skills in $SOURCE_DIR"; exit 1; }
```

## Step 3: Execute install/uninstall

### If --uninstall:

```bash
removed=0
for dir in "$TARGET_DIR"/gsd-kb-*; do
  [ -d "$dir" ] && rm -rf "$dir" && removed=$((removed+1))
done
echo "✓ Removed $removed KB skills from $TARGET_DIR"
```

Also remove KB CLI if present:
```bash
rm -rf "$HOME/.claude/knowledge-base" 2>/dev/null && echo "  Removed knowledge-base CLI"
```

STOP after uninstall.

### If install (default):

```bash
mkdir -p "$TARGET_DIR"
count=0

for skill_dir in "$SOURCE_DIR"/gsd-kb-*; do
  [ ! -d "$skill_dir" ] && continue
  skill_name=$(basename "$skill_dir")
  target_path="$TARGET_DIR/$skill_name"

  # Remove existing
  rm -rf "$target_path"

  if [ "$MODE" = "link" ]; then
    ln -s "$skill_dir" "$target_path"
  else
    cp -r "$skill_dir" "$target_path"
  fi
  count=$((count+1))
done
```

### Install knowledge-base CLI:

```bash
KB_CLI_SOURCE="$REPO_ROOT/knowledge-base"
KB_CLI_TARGET="$HOME/.claude/knowledge-base"

if [ -f "$KB_CLI_SOURCE/packages/cli/__main__.py" ]; then
  rm -rf "$KB_CLI_TARGET"
  if [ "$MODE" = "link" ]; then
    ln -s "$KB_CLI_SOURCE" "$KB_CLI_TARGET"
  else
    cp -r "$KB_CLI_SOURCE" "$KB_CLI_TARGET"
  fi
  echo "  ✓ knowledge-base CLI installed"
else
  echo "  ⚠️ knowledge-base CLI not found — graph/batch-fill unavailable"
fi
```

## Step 4: Verify installation

```bash
# Count installed skills
installed=$(ls -d "$TARGET_DIR"/gsd-kb-* 2>/dev/null | wc -l)

# Check a key skill is readable
if [ -f "$TARGET_DIR/gsd-kb-query/SKILL.md" ]; then
  verify="✓"
else
  verify="✗"
fi

# Check CLI
if [ -f "$HOME/.claude/knowledge-base/packages/cli/__main__.py" ]; then
  cli_status="✓ available"
else
  cli_status="✗ missing"
fi
```

## Step 5: Report

```
GSD > KB-INSTALL Complete
════════════════════════════════════════════════════════════
Source:     {REPO_ROOT}/skills/
Target:     {TARGET_DIR}
Mode:       {copy|link}
────────────────────────────────────────────────────────────
Skills installed:  {count}
Verification:      {verify}
KB CLI:            {cli_status}
════════════════════════════════════════════════════════════

Available commands (restart session to activate):
  /gsd-kb-init              — Scaffold KB structure for a module
  /gsd-kb-fill              — Deep semantic fill (batch + AI)
  /gsd-kb-query             — Query knowledge graph
  /gsd-kb-gen-tests         — Generate test cases from KB
  /gsd-kb-deploy            — Deploy app or connect remote + auto-generate ENV-CONFIG
  /gsd-kb-enforce-locators  — Inject data-testid for Playwright

Quick start:
  /gsd-kb-init --module myapp --source ./src --output ./docs
```

</process>

<notes>
- Safe to re-run: overwrites existing skills (idempotent)
- `--mode link` is for developers working on skills — changes reflect immediately
- `--mode copy` is for end users — no dependency on repo location after install
- Restart Claude Code session after install for skills to be picked up
- knowledge-base CLI requires Python 3.9+ (for graph build, batch-fill)
- Does NOT install to .claude/skills/ inside a project — only user-level global skills
</notes>
