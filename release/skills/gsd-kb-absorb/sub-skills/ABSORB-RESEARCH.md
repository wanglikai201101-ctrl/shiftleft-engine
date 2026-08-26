# Sub-skill: Absorb Research Artifacts

## Purpose

Extract KB patches from research/investigation documents — terminology updates, architecture decisions.

## Input

1. **Research files** — `.planning/research/*.md` contents
2. **Target KB docs** — REQ docs (领域术语), MODULE.md (architecture)

## What to extract

From each research document:

**1. Terminology updates** (→ patch REQ `### 领域术语` or MODULE.md `## 领域术语`):
- Research defines/clarifies a domain concept → new glossary row
- Research reveals existing term is used incorrectly → CORRECT glossary row

Pattern recognition:
- "X means ..." / "X refers to ..." / "the distinction between X and Y is ..."
- Comparison tables listing term definitions
- Architecture decision records (ADR) defining vocabulary

**2. Architecture context** (→ append to MODULE.md `## 架构说明` or relevant REQ 业务描述):
- Research concludes with architecture decision → relevant context for KB
- Only extract the DECISION, not the full deliberation

Pattern recognition:
- "Decision: use X over Y because ..." → architecture note
- "Conclusion: ..." → extractable decision

**3. Integration patterns** (→ patch API doc `## 依赖接口` or `## 被依赖接口`):
- Research about system integration → new dependency relationships
- "Service A calls Service B via ..." → upstream/downstream link

## Output format

```json
{
  "patches": [
    {
      "target_doc": "requirements/REQ-SB-004.md",
      "section": "### 领域术语",
      "action": "APPEND",
      "content": "| 知识注入 | knowledge.inject | inject_knowledge_text() | 将文本/文件内容写入 BillingAgent 的知识库 | 区分于\"上传文件\"（只存储不注入） |",
      "source_file": "research/knowledge-sync-strategy.md",
      "reason": "research 明确了知识注入的精确定义"
    }
  ]
}
```

## Rules

- Only extract CONCRETE definitions/decisions — skip open questions and alternatives
- Terminology must have at least: 术语 + 业务含义 (other columns can be "—")
- Architecture notes: one sentence max, factual, not opinion
- If research is still in-progress (no conclusion section) → skip entirely
- Don't extract implementation details (code patterns) — only business/domain knowledge
