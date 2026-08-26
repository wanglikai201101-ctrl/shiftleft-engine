# Sub-skill: Absorb Verification & Deviation Artifacts

## Purpose

Extract KB corrections from verification reports (test pass/fail) and deviation records (scope changes).

## Input

1. **VERIFICATION.md files** — `.planning/phases/*/VERIFICATION.md`
2. **DEVIATION.md files** — `.planning/phases/*/DEVIATION.md`
3. **Target KB docs** — REQ docs (TP table, 业务规则)

## What to extract from VERIFICATION.md

**1. TP result corrections** (→ CORRECT REQ `## 最小可测单元拆解` rows):
- Test failed because expected result was wrong in doc → correct 预期结果 column
- Test passed with different value than documented → correct 预期结果 column

Pattern recognition:
- "TP-SB-003-04: FAIL — expected 200 but got 201" → correct expected to 201
- "TP-SB-003-09: FAIL — actual response missing field X" → correct 预期结果
- "PASS with note: actual status is 'active' not 'running'" → correct

**2. New test points discovered** (→ APPEND to TP table):
- Verification found untested scenarios → new TP rows

Pattern recognition:
- "Gap: no test for concurrent publish" → new TP
- "Missing coverage: auth token expiry during long operation" → new TP

**3. DB assertion corrections** (→ CORRECT `DB断言` column):
- "Actual DB state after test: status='stopped' not 'idle'" → correct assertion

## What to extract from DEVIATION.md

**1. Business rule changes** (→ CORRECT/APPEND REQ `### 业务规则与约束`):
- Deviation documents a deliberate behavior change → update the rule

Pattern recognition:
- "Changed from X to Y because ..." → correct existing BR
- "New constraint: ..." → new BR row
- "Removed restriction: ..." → mark BR as deprecated (add strikethrough or note)

**2. Scope adjustments** (→ CORRECT REQ `## 业务描述` or `## 需求概述`):
- If requirement scope was explicitly expanded/reduced
- Only patch 业务描述 if the change is significant (not minor wording)

Pattern recognition:
- "Descoped: feature X will not be in this phase" → note in 业务描述
- "Added: Y is now in scope" → expand 业务描述

**3. TP removals/additions** (→ patch TP table):
- "TP-SB-003-14 is no longer relevant because ..." → mark as `[DEPRECATED]` in 测试点描述
- "New TP needed for ..." → APPEND row

## Output format

```json
{
  "patches": [
    {
      "target_doc": "requirements/REQ-SB-003.md",
      "section": "## 最小可测单元拆解",
      "action": "CORRECT",
      "row_key": "TP-SB-003-04",
      "column": "预期结果",
      "old_value": "200, 返回 {agent_id, version, s3_key}",
      "new_value": "201, 返回 {agent_id, version, s3_key, created_at}",
      "source_file": "phases/p3/VERIFICATION.md",
      "reason": "实际测试返回 201 Created（非 200），且包含 created_at 字段"
    },
    {
      "target_doc": "requirements/REQ-SB-003.md",
      "section": "### 业务规则与约束",
      "action": "CORRECT",
      "row_key": "BR-SB-003-06",
      "column": "规则描述",
      "old_value": "发布前需 health check（5s 超时）",
      "new_value": "发布前需 health check（10s 超时，可配置）",
      "source_file": "phases/p3/DEVIATION.md",
      "reason": "偏差记录：超时从 5s 调整为 10s"
    }
  ]
}
```

## Rules

- CORRECT action requires: row_key (唯一标识行) + column (哪列) + old_value + new_value
- CORRECT only when there's clear evidence the doc is WRONG (test result / explicit deviation)
- Don't "correct" based on opinion or preference — only facts
- Deprecated TPs: don't delete row, add `[DEPRECATED: {reason}]` prefix to 测试点描述
- Scope changes: only patch 业务描述 for MAJOR changes (not typos or rewording)
- If verification passed all TPs → no patches needed from that file (skip)
