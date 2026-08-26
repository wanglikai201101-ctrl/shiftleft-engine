---
name: gsd-kb-fill-config
description: "Config auto-discovery: rule engines, provisioners, workflow definitions, feature flags, env-driven config classes"
argument-hint: "--module <name> --source <path> --output <path> [--force]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Grep
  - Glob
  - Agent
---



<critical-rules>
🚫 HALT — 逐条阅读以下规则，违反任何一条 = 输出无效，必须删除重做

1. 🚫 NEVER write files outside `$OUTPUT/$MODULE/config/` — 禁止写入 apis/, pages/, tech/, graph/, tests/, requirements/, storage/, jobs/
2. 🚫 NEVER create files with non-standard names — only `{config-name}.md` format (lowercase, hyphen-separated)
   - ✅ Allowed: `langfuse-provisioner.md`, `billing-recognition-rules.md`, `feature-flags.md`
   - ❌ Forbidden: `SERVICE-*.md`, `_INDEX.md`, `SUMMARY.md`, `README.md`
3. 🚫 NEVER document non-config concerns — this skill documents CONFIGURATION ENTITIES only
   - ❌ Forbidden: API endpoints, page docs, table schemas, job docs, service class docs
   - ✅ Allowed: config classes, rule definitions, provisioners, feature flags, workflow definitions, env-driven settings
4. 🚫 NEVER ignore --force flag — force 模式下必须重写，禁止判断"已符合规范"跳过

违反以上任何一条 = 立即停止，输出 "BOUNDARY VIOLATION: {which rule}" 并退出。
</critical-rules>

<objective>
Discover and generate configuration documentation for a module.

Searches for configuration-driven entities:
1. Config classes (Pydantic Settings, dataclasses with env vars, config providers)
2. Rule engines (recognition rules, billing rules, matching logic)
3. Provisioners (service provisioners, resource provisioners)
4. Workflow/pipeline definitions (state machines, step configs)
5. Feature flags and toggles
6. Field mappings and data transformation configs

A module with provisioners, rule engines, or env-driven config classes
ALWAYS has config entities — this skill must find and document them.
</objective>

<process>

## Step 1: Parse arguments

Extract from `$ARGUMENTS`:
- `--module <name>` (required): module name
- `--source <path>` (required): backend source code directory
- `--output <path>` (optional, default: `.planning/ontology`): documentation output directory
- `--force` (optional): re-generate ALL config docs, overwriting existing content. Without --force, create new config docs for undocumented configs and apply UPDATE-FIRST incremental edits to existing template-compliant docs.

**🔒 --force 行为定义（强制执行，不可自行跳过）：**

当传入 `--force` 时：
- **必须**重新读取源代码并完整重写每个 config 文档
- **禁止**判断"现有文件已符合规范"而跳过重写
- **禁止**输出"文件保持现状"然后不做任何修改
- 唯一不覆盖的是 `<!-- manual -->` 标记的段落

Determine PROJECT_ROOT: walk up from `--source` until `pyproject.toml` / `package.json` / `setup.py` found.

## Step 2: Discover configuration entities

🚫 扫描范围必须限定在 `--source` 路径内，不得向上扩展到 PROJECT_ROOT 全局扫描。
只有当 `--source` 内没有找到任何 config 时，才 fallback 到 PROJECT_ROOT，但 fallback 时必须用 module 名做路径过滤。

### Strategy 1: Config/Settings classes (Python)
```bash
grep -rn "BaseSettings\|BaseConfig\|@dataclass.*config\|class.*Config.*:\|class.*Settings.*:" "$SOURCE" --include="*.py" | grep -v .venv | grep -v node_modules | grep -v __pycache__
```

### Strategy 2: Provisioners and providers
```bash
grep -rn "class.*Provis\|class.*Provider\|class.*Factory\|provision\|_provisioner\|_provider" "$SOURCE" --include="*.py" | grep -v .venv | grep -v __pycache__
```

### Strategy 3: Rule engines and matching logic
```bash
grep -rn "class.*Rule\|class.*Matcher\|class.*Evaluator\|RULES\s*=\|rules_config\|rule_engine" "$SOURCE" --include="*.py" | grep -v .venv | grep -v __pycache__
```

### Strategy 4: Feature flags and toggles
```bash
grep -rn "FEATURE_\|feature_flag\|FeatureFlag\|toggle\|is_enabled\|LaunchDarkly\|unleash" "$SOURCE" --include="*.py" --include="*.ts" --include="*.tsx" | grep -v .venv | grep -v node_modules
```

### Strategy 5: Workflow/pipeline definitions
```bash
grep -rn "class.*Workflow\|class.*Pipeline\|class.*StateMachine\|STEPS\s*=\|stages\s*=\|transitions\s*=" "$SOURCE" --include="*.py" | grep -v .venv | grep -v __pycache__
```

### Strategy 6: Environment-driven config (env vars with business meaning)
```bash
grep -rn "env_prefix\|Field.*env=\|os\.environ\.\|os\.getenv\(" "$SOURCE" --include="*.py" | grep -v .venv | grep -v __pycache__
```
Filter: only include files where ≥3 env vars are read (indicates a config class, not ad-hoc usage).

### Strategy 7: JSON/YAML config files
```bash
find "$SOURCE" -name "*.config.json" -o -name "*.config.yaml" -o -name "*.config.yml" -o -name "rules.json" -o -name "rules.yaml" | grep -v node_modules | grep -v .venv
```

## Step 3: Classify and generate config docs

For each discovered config entity, determine its type:

| Discovery pattern | Config type |
|---|---|
| BaseSettings / Config class | 系统配置 |
| Provisioner / Provider / Factory | 资源配置（Provisioner） |
| Rule / Matcher / Evaluator | 规则配置 |
| FeatureFlag / toggle | 功能开关 |
| Workflow / Pipeline / StateMachine | 流程配置 |
| JSON/YAML config files | 数据配置文件 |

**🔒 UPDATE-FIRST 写入规则（更新优先，强制执行）：**
- 目标文档 **已存在** 且符合模板规范（所有必需 `##` 节齐全、关键字段无 `待补充`）→ **先 READ** 该文件，再用 **Edit 工具** 只修改受影响的节（更新值、插入/更新行、追加 `变更记录` 行）
- **逐字节保留**所有未修改内容，**包括**文件现有的行尾风格（CRLF 与 LF 必须保持原样）
- 完整 `Write` 仅用于：全新文档、`--force`、或文档缺失必需模板节（schema 迁移）
- Preserve `<!-- manual -->` sections

### Config doc template

```markdown
# {config_name} — {description}

> 源文件: `{file_path}`

## 基本信息

| 字段 | 值 |
|------|-----|
| 配置类型 | {系统配置/资源配置/规则配置/功能开关/流程配置/数据配置} |
| 配置名称 | {唯一标识} |
| 模块 | {module} |
| 负责人 | 待补充 |
| 需求来源 | 待补充 |
| 当前版本 | v1.0 |
| 状态 | 启用 |

## 配置参数

| 参数名 | 类型 | 必填 | 默认值 | 环境变量 | 说明 |
|--------|------|------|--------|---------|------|
| {param} | {type} | {是/否} | {default} | {ENV_VAR or —} | {description} |

## 配置规则

{描述该配置的业务逻辑、匹配条件、执行动作}

## 配置示例

```json
{example JSON showing typical configuration}
```

## 关联需求

| 需求编号 | 说明 |
|---------|------|
| 待补充 | 待补充 |

## 关联接口

| 接口 | 使用方式 | 说明 |
|------|---------|------|

## 关联数据库

| 表 | 字段 | 说明 |
|-----|------|------|

## 变更记录

| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 影响范围 |
|------|------|--------|--------|--------|--------|
| v1.0 | 待补充 | scaffold 自动生成 | 无（新建） | 从代码反推骨架 | 待补充 |
```

## Step 4: Handle "no config" case

**If genuinely no config entities exist** (no config classes, no provisioners, no rules, no feature flags):
- Remove the empty `$OUTPUT/$MODULE/config/` directory (do not leave empty folders)
- Update MODULE.md "模块资产清单" table: `| 配置文档 | 0（该模块无配置实体） | config/ |`
- Do NOT leave a bare "0" — always annotate the reason

**IMPORTANT**: A module with provisioners, rule engines, or settings classes ALWAYS has config entities — do NOT report "0" for such modules.

## Step 5: Report

```
GSD > KB-FILL-CONFIG Complete
────────────────────────────────────────────────────────────
Module:       {module}
Configs found: {N} (settings: {n1}, provisioners: {n2}, rules: {n3}, flags: {n4}, workflows: {n5})
Config docs:  {generated}/{total}
────────────────────────────────────────────────────────────
```

</process>

<notes>
- Safe to re-run: existing template-compliant config docs are updated incrementally (UPDATE-FIRST Edit); new docs are created for undocumented configs; only --force does a full overwrite
- With --force: overwrites all config docs with fresh content from source code
- Recognizes both explicit (Settings classes, provisioners) and implicit (env var patterns, rule arrays) config entities
- A module with provisioners/rule engines/settings classes MUST report configs
- Config docs feed into the knowledge graph as "config" type nodes
</notes>
