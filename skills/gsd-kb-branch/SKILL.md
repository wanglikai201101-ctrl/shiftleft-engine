---
name: gsd-kb-branch
description: "Create an isolated work branch before code changes — ensures failed modifications don't pollute the source branch."
argument-hint: "[--prefix <prefix>] [--from <base-ref>] [--name <branch-name>]"
allowed-tools:
  - Bash
  - Read
  - Write
  - Grep
  - Glob
---

<objective>
Create a clean, isolated branch before any code modification begins. This guarantees that if the modification fails, crashes, or produces bad code, the original branch remains untouched.

Use cases:
- Pipeline `--do` execution: branch before spawning gsd-quick/debug/plan
- Manual safety: user wants to try something risky without polluting current branch
- Progressive mode: each round can optionally get its own branch

The branch is created FROM the current HEAD (or specified base) and named with a predictable convention so it can be found, merged, or discarded later.
</objective>

<process>

## Step 1: Detect current state

```bash
# Current branch name
CURRENT_BRANCH=$(git branch --show-current)

# Check for uncommitted changes
DIRTY=$(git status --porcelain)

# Current HEAD
HEAD_REF=$(git rev-parse --short HEAD)
```

**Decision:**
- If `DIRTY` is non-empty → stash changes first:
  ```bash
  git stash push -u -m "kb-branch: auto-stash before branching"
  ```
  Record `STASHED=true` for later.
- If `DIRTY` is empty → `STASHED=false`.

## Step 2: Determine branch name

**Priority:**
1. If `--name` provided → use as-is (validate: no spaces, no special chars except `-_/`)
2. Otherwise, auto-generate:

```bash
# Components
PREFIX="${prefix:-pipeline}"   # default "pipeline", or from --prefix
DATE=$(date +%Y%m%d)
TIME=$(date +%H%M)

# If --do description available, derive slug
SLUG=$(echo "{description}" | head -c 40 | tr ' ' '-' | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]//g')

BRANCH_NAME="${PREFIX}/${DATE}-${TIME}-${SLUG}"
```

**Naming convention:** `{prefix}/{YYYYMMDD}-{HHMM}-{slug}`
- Examples: `pipeline/20260707-1430-add-batch-delete`, `pipeline/20260707-1500-fix-websocket`

## Step 3: Create branch

```bash
BASE_REF="${from:-HEAD}"   # default HEAD, or from --from

# Create and switch
git checkout -b "$BRANCH_NAME" "$BASE_REF"
```

**Verify:**
```bash
# Confirm we're on the new branch
ACTUAL=$(git branch --show-current)
if [ "$ACTUAL" != "$BRANCH_NAME" ]; then
  echo "❌ BRANCH FAILED: expected $BRANCH_NAME, got $ACTUAL"
  exit 1
fi
```

## Step 4: Restore stashed changes (if any)

```bash
if [ "$STASHED" = "true" ]; then
  git stash pop
fi
```

## Step 5: Output

```
✅ BRANCH CREATED
   From: {CURRENT_BRANCH} @ {HEAD_REF}
   New:  {BRANCH_NAME}
   Base: {BASE_REF}
   Stash: {restored|none}
   
   Safe to modify. On failure: git checkout {CURRENT_BRANCH}
   On success: merge back or create PR.
```

Write branch metadata to state file (if pipeline context):
```bash
BRANCH_META="{output}/{module}/BRANCH-STATE.json"
cat > "$BRANCH_META" << EOF
{
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "source_branch": "{CURRENT_BRANCH}",
  "source_ref": "{HEAD_REF}",
  "work_branch": "{BRANCH_NAME}",
  "stashed": {STASHED},
  "status": "active"
}
EOF
```

</process>

<rollback>
## Rollback (on failure)

If the pipeline or modification fails and the user wants to discard:

```bash
# Switch back to original branch
git checkout {CURRENT_BRANCH}

# Delete the failed work branch
git branch -D {BRANCH_NAME}
```

If stash was applied and changes need to be preserved:
```bash
git stash push -u -m "kb-branch: preserving changes from failed branch {BRANCH_NAME}"
git checkout {CURRENT_BRANCH}
git branch -D {BRANCH_NAME}
git stash pop
```
</rollback>

<merge>
## Merge back (on success)

After pipeline completes successfully:

```bash
# Option A: Fast-forward merge (clean history)
git checkout {CURRENT_BRANCH}
git merge --ff-only {BRANCH_NAME}
git branch -d {BRANCH_NAME}

# Option B: Squash merge (single commit)
git checkout {CURRENT_BRANCH}
git merge --squash {BRANCH_NAME}
git commit -m "feat: {description} (pipeline delivery)"
git branch -d {BRANCH_NAME}

# Option C: Keep branch, create PR (for review) — MANUAL ONLY, never auto-executed by pipeline
# 🚫 Do NOT push automatically. User must explicitly request push.
# git push -u origin {BRANCH_NAME}
# Then use /gsd-pr-branch or gh pr create
```
</merge>

<integration>
## Pipeline Integration

In the complete product, this skill is called by the pipeline orchestrator at Step 0b (before spawning the execution agent); in this open-source subset you invoke `/gsd-kb-branch` directly.

In pipeline SKILL.md, the call is:
```
Agent(prompt: "/gsd-kb-branch --prefix pipeline --name {auto-generated}")
```

After pipeline success → merge back automatically (Option A by default).
After pipeline failure → leave branch, report to user for manual decision.

The pipeline's PIPELINE-STATE.json should record:
```json
{
  "branch": {
    "source": "feature/main-work",
    "work": "pipeline/20260707-1430-add-batch-delete",
    "status": "active|merged|discarded"
  }
}
```
</integration>

<notes>
- Branch isolation is the safest way to protect ongoing work from pipeline modifications
- Naming convention allows easy identification and cleanup of abandoned pipeline branches
- Stash handling ensures no uncommitted work is lost during branch creation
- BRANCH-STATE.json enables automated merge/discard decisions by the pipeline orchestrator
- For progressive mode: all rounds share one work branch (not one per round) — the round isolation comes from the PIPELINE-STATE.json tracking
- This skill is idempotent: if already on a pipeline/* branch, it skips creation and reports existing branch
</notes>
