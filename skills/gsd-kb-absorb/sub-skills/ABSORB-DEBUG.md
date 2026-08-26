# Sub-skill: Absorb Debug Artifacts

## Purpose

Extract actionable KB patches from debug session artifacts (bug root cause analysis, fix records).

## Input

1. **Debug files** — `.planning/debug/*.md` contents
2. **Target KB docs** — existing REQ docs (边缘场景, 业务规则) and API docs (错误码)

## What to extract

From each debug file, look for:

**1. New edge cases** (→ append to REQ `## 边缘场景` table):
- Root cause description → 场景描述
- Trigger condition → 触发条件
- Fix behavior → 预期行为
- Source: `debug/{filename}`

Pattern recognition:
- "root cause: ..." → edge case scenario
- "reproduced when ..." → trigger condition
- "fixed by ..." → expected behavior (the fix IS the correct behavior)

**2. Business rule corrections** (→ correct/append to REQ `### 业务规则与约束`):
- If debug reveals a rule was wrong → CORRECT existing BR row
- If debug reveals an undocumented rule → APPEND new BR row

Pattern recognition:
- "the actual behavior is X, not Y" → correct existing rule
- "missing validation for ..." → new rule

**3. New error codes** (→ append to API doc `## 错误码` table):
- If the bug involved an unexpected HTTP status code
- If the fix added a new error response

Pattern recognition:
- "returns 500 instead of ..." → error code was missing
- "added 409 check for ..." → new error code row

## Output format

```json
{
  "patches": [
    {
      "target_doc": "requirements/REQ-SB-003.md",
      "section": "## 边缘场景",
      "action": "APPEND",
      "content": "| EDGE-SB-003-{next} | {描述} | {触发条件} | {预期行为} | debug/{source} |",
      "source_file": "debug/{filename}.md",
      "reason": "{why this should be in KB}"
    },
    {
      "target_doc": "apis/POST-{agent_id}-publish.md",
      "section": "## 错误码",
      "action": "APPEND",
      "content": "| 504 | S3 presigned URL 上传超时 | {\"detail\": \"Upload timeout\"} | debug fix: router.py:4420 |",
      "source_file": "debug/{filename}.md",
      "reason": "新发现的错误码"
    }
  ]
}
```

## Rules

- Only extract ACTIONABLE patches — skip general discussion/investigation notes
- Edge case must have all 3 fields filled (描述 + 触发条件 + 预期行为)
- Error codes must have HTTP status + trigger condition + response body
- 防重复（幂等）：APPEND 前先查目标 section 是否已含该内容（或该 ID，如 EDGE-xxx-NN / BR-xxx-NN / 错误码行）——已存在则跳过（上次已写入），不存在才读现有表分配下一个新 ID
- If debug file mentions an API but the API doc doesn't exist → skip (don't create docs)
- If unsure whether something is KB-worthy → include it with `"confidence": "low"` in output
