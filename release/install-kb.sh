#!/usr/bin/env bash
# install-kb.sh — One-click install of GSD Knowledge Base + gsd-core dev skills + engine
# Usage: bash scripts/install-kb.sh [--link|--copy] [--target <dir>] [--engine-target <dir>]
#
# Installs:
#   1. All gsd-kb-* skills from this repo         →  $TARGET_DIR (default ~/.claude/skills)
#   2. All 9 gsd-core dev skills (release-skills)  →  $TARGET_DIR (default ~/.claude/skills)
#   3. The gsd-core engine snapshot (release/gsd-core) → $ENGINE_TARGET_DIR (default ~/.claude/gsd-core)
#   4. Engine companion scripts (release/scripts)      → ~/.claude/scripts (sibling of gsd-core)
# Default: copy mode (safe, no broken symlinks if repo moves)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Component sources resolve relative to THIS script's directory, so the
# installer works from a release-only distribution (components flat at the
# repo root) AND from <repo>/release inside a full clone. The legacy entry
# point scripts/install-kb.sh falls back through to the sibling release/ dir.
KB_SOURCE_DIR="$SCRIPT_DIR/skills"
DEV_SOURCE_DIR="$SCRIPT_DIR/release-skills"
ENGINE_SOURCE_DIR="$SCRIPT_DIR/gsd-core"
SCRIPTS_SOURCE_DIR="$SCRIPT_DIR/scripts"
KB_CLI_SOURCE_DIR="$SCRIPT_DIR/knowledge-base"
if [ ! -d "$ENGINE_SOURCE_DIR" ]; then
  REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
  RELEASE_DIR="$REPO_ROOT/release"
  KB_SOURCE_DIR="$RELEASE_DIR/skills"
  DEV_SOURCE_DIR="$RELEASE_DIR/release-skills"
  ENGINE_SOURCE_DIR="$RELEASE_DIR/gsd-core"
  SCRIPTS_SOURCE_DIR="$RELEASE_DIR/scripts"
  KB_CLI_SOURCE_DIR="$RELEASE_DIR/knowledge-base"
fi

# Defaults
MODE="copy"
TARGET_DIR="${HOME}/.claude/skills"
ENGINE_TARGET_DIR=""
SCRIPTS_TARGET_DIR=""

# Parse args
while [[ $# -gt 0 ]]; do
  case $1 in
    --link) MODE="link"; shift ;;
    --copy) MODE="copy"; shift ;;
    --target) TARGET_DIR="$2"; shift 2 ;;
    --engine-target) ENGINE_TARGET_DIR="$2"; shift 2 ;;
    --scripts-target) SCRIPTS_TARGET_DIR="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: bash scripts/install-kb.sh [--link|--copy] [--target <dir>] [--engine-target <dir>]"
      echo ""
      echo "Options:"
      echo "  --copy           Copy skill files (default, safe)"
      echo "  --link           Symlink skill dirs (dev mode, auto-updates)"
      echo "  --target         Override skill target dir (default: ~/.claude/skills)"
      echo "  --engine-target  Override engine install dir (default: ~/.claude/gsd-core)"
      echo "  --scripts-target Override companion scripts dir (default: sibling of engine dir)"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# Normalize target (expand literal tilde, strip trailing slash)
TARGET_DIR="${TARGET_DIR/#\~/$HOME}"
TARGET_DIR="${TARGET_DIR%/}"

# Engine target defaults to a sibling of the skills target (e.g. ~/.claude/gsd-core)
if [ -z "$ENGINE_TARGET_DIR" ]; then
  ENGINE_TARGET_DIR="$(dirname "$TARGET_DIR")/gsd-core"
else
  ENGINE_TARGET_DIR="${ENGINE_TARGET_DIR/#\~/$HOME}"
  ENGINE_TARGET_DIR="${ENGINE_TARGET_DIR%/}"
fi

# Scripts target defaults to a sibling of the engine target (e.g. ~/.claude/scripts)
if [ -z "$SCRIPTS_TARGET_DIR" ]; then
  SCRIPTS_TARGET_DIR="$(dirname "$ENGINE_TARGET_DIR")/scripts"
else
  SCRIPTS_TARGET_DIR="${SCRIPTS_TARGET_DIR/#\~/$HOME}"
  SCRIPTS_TARGET_DIR="${SCRIPTS_TARGET_DIR%/}"
fi

# Ensure targets exist
mkdir -p "$TARGET_DIR"
mkdir -p "$(dirname "$ENGINE_TARGET_DIR")"
mkdir -p "$(dirname "$SCRIPTS_TARGET_DIR")"

install_dir() {
  # install_dir <source> <target> <label>
  local src="$1" dst="$2" label="$3"
  if [ "$MODE" = "link" ]; then
    rm -rf "$dst"
    ln -s "$src" "$dst"
    echo "  [link] $label → $dst"
  else
    rm -rf "$dst"
    cp -r "$src" "$dst"
    echo "  [copy] $label → $dst"
  fi
}

# Find KB skills
KB_SKILLS=$(find "$KB_SOURCE_DIR" -maxdepth 1 -type d -name "gsd-kb-*" | sort)
# Find gsd-core dev skills
DEV_SKILLS=$(find "$DEV_SOURCE_DIR" -maxdepth 1 -type d -name "gsd-*" | sort)
COUNT=0

echo "GSD Installer (Knowledge Base + gsd-core engine)"
echo "════════════════════════════════════════════"
echo "KB skills source:   $KB_SOURCE_DIR"
echo "Dev skills source:  $DEV_SOURCE_DIR"
echo "Engine source:      $ENGINE_SOURCE_DIR"
echo "Scripts source:     $SCRIPTS_SOURCE_DIR"
echo "Skill target:       $TARGET_DIR"
echo "Engine target:      $ENGINE_TARGET_DIR"
echo "Scripts target:     $SCRIPTS_TARGET_DIR"
echo "Mode:               $MODE"
echo "────────────────────────────────────────────"

# 1) Knowledge Base skills (gsd-kb-*)
for skill_dir in $KB_SKILLS; do
  install_dir "$skill_dir" "$TARGET_DIR/$(basename "$skill_dir")" "$(basename "$skill_dir")"
  COUNT=$((COUNT + 1))
done

# 2) gsd-core development skills (release/release-skills/gsd-*)
for skill_dir in $DEV_SKILLS; do
  install_dir "$skill_dir" "$TARGET_DIR/$(basename "$skill_dir")" "$(basename "$skill_dir")"
  COUNT=$((COUNT + 1))
done

echo "────────────────────────────────────────────"
echo "✓ Installed $COUNT skills to $TARGET_DIR"

# 3) gsd-core engine snapshot
if [ -d "$ENGINE_SOURCE_DIR" ]; then
  install_dir "$ENGINE_SOURCE_DIR" "$ENGINE_TARGET_DIR" "gsd-core engine"
else
  echo "  [warn] engine source not found at $ENGINE_SOURCE_DIR"
  echo "         gsd-core development skills will not run without the engine"
fi

# 4) Engine companion scripts (release/scripts → scripts sibling of engine)
if [ -d "$SCRIPTS_SOURCE_DIR" ]; then
  install_dir "$SCRIPTS_SOURCE_DIR" "$SCRIPTS_TARGET_DIR" "scripts"
else
  echo "  [warn] scripts source not found at $SCRIPTS_SOURCE_DIR"
  echo "         gsd-core fix-slash-commands.cjs / kb probe will not be available"
fi

echo ""
echo "Also needs: knowledge-base CLI (for graph build, batch-fill)"
if [ -d "$KB_CLI_SOURCE_DIR/packages/cli" ]; then
  KB_CLI_TARGET="${HOME}/.claude/knowledge-base"
  if [ ! -d "$KB_CLI_TARGET" ]; then
    mkdir -p "$(dirname "$KB_CLI_TARGET")"
    if [ "$MODE" = "link" ]; then
      ln -s "$KB_CLI_SOURCE_DIR" "$KB_CLI_TARGET"
      echo "  [link] knowledge-base CLI → $KB_CLI_TARGET"
    else
      cp -r "$KB_CLI_SOURCE_DIR" "$KB_CLI_TARGET"
      echo "  [copy] knowledge-base CLI → $KB_CLI_TARGET"
    fi
  else
    echo "  [skip] knowledge-base CLI already at $KB_CLI_TARGET"
  fi
else
  echo "  [warn] $KB_CLI_SOURCE_DIR/packages/cli not found"
  echo "         Graph build and batch-fill will not work without it"
fi

echo ""
echo "Done. Restart Claude Code to pick up new skills."
echo "Available commands: /gsd-kb-init, /gsd-kb-fill, /gsd-kb-gen-tests, /gsd-kb-query"
echo "Plus gsd-core dev skills: /gsd-quick, /gsd-debug, /gsd-spike, /gsd-secure-phase, /gsd-code-review, /gsd-new-project, /gsd-fast, /gsd-plan-phase, /gsd-execute-phase"