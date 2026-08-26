# Sub-skill: Absorb Quick Task Artifacts

## Purpose

Extract KB patches from quick task summaries — API changes, new fields, state transition updates.

## Input

1. **Quick SUMMARY files** — `.planning/quick/*/SUMMARY.md` contents (preferred source)
2. **Quick PLAN files** — `.planning/quick/*/PLAN.md` with `status: complete` + `## Result` section (used when SUMMARY.md doesn't exist — this is the format produced by pipeline-fast)
3. **Target KB docs** — API docs, Storage docs, REQ state matrices

## What to extract

From each quick task (SUMMARY.md OR PLAN.md with `## Result`):

**1. API parameter changes** (→ patch API doc `## 请求参数` or `## 响应结构`):
- "added parameter X to endpoint Y" → APPEND param row
- "changed response to include Z" → APPEND response field row
- "removed field W" → mark as deprecated (don't delete)

Pattern recognition:
- Code diffs showing new `Body(...)` / `Query(...)` params
- New fields in response model
- Changed validation rules

**2. Storage schema changes** (→ patch Storage doc `## 字段定义`):
- "added column X to table Y" → APPEND field row
- "changed type of Z" → CORRECT existing row
- "added index on ..." → APPEND to indexes section

**3. State transition changes** (→ patch REQ `### 状态转换矩阵`):
- "added new status value" → APPEND matrix rows
- "changed transition guard" → CORRECT existing row
- "new status: 'maintenance'" → new rows for all transitions involving it

**4. New API endpoints** (→ flag for manual follow-up, don't auto-create):
- If summary mentions creating a new endpoint → output as "NEEDS_NEW_DOC" advisory
- Don't attempt to create full API docs from summary alone

## Output format

```json
{
  "patches": [
    {
      "target_doc": "apis/POST-{agent_id}-publish.md",
      "section": "## 请求参数",
      "action": "APPEND",
      "content": "| changelog_note | string | 否 | 用户输入 | 可选发布备注 |",
      "source_file": "quick/20260701-add-changelog-note/SUMMARY.md",
      "reason": "quick task 新增了发布备注参数"
    }
  ],
  "advisories": [
    {
      "type": "NEEDS_NEW_DOC",
      "description": "New endpoint POST /api/v1/sandbox/{agent_id}/fork detected",
      "source_file": "quick/20260702-fork-agent/SUMMARY.md"
    }
  ]
}
```

## Rules

- Only extract from COMPLETED quick tasks:
  - SUMMARY.md with status=complete, OR
  - PLAN.md with `status: complete` in frontmatter + `## Result` section present
- Skip in-progress or abandoned tasks
- APPEND is safe; CORRECT requires matching existing row by key field (param name / column name)
- For state transitions: verify new status value actually exists in code before patching
- Advisories (NEEDS_NEW_DOC) → reported in ABSORB-REPORT.md for human follow-up
- When extracting from PLAN.md `## Result`: use the commit hash + files changed + summary to infer patches (same extraction logic as SUMMARY.md)
