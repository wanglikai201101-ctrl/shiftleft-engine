---
name: gsd-kb-fill-integration
description: "Integration auto-discovery: external API clients, connectors, adapters, EDI/ERP/payment integrations"
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

1. 🚫 NEVER write files outside `$OUTPUT/$MODULE/integration/` — 禁止写入 apis/, pages/, tech/, graph/, tests/, requirements/, storage/, jobs/, config/
2. 🚫 NEVER create files with non-standard names — only `{connector-name}.md` format (lowercase, hyphen-separated)
   - ✅ Allowed: `netsuite-invoice.md`, `stripe-payment.md`, `edi-850-purchase-order.md`
   - ❌ Forbidden: `SERVICE-*.md`, `_INDEX.md`, `SUMMARY.md`, `README.md`
3. 🚫 NEVER document non-integration concerns — this skill documents EXTERNAL SYSTEM INTEGRATIONS only
   - ❌ Forbidden: internal API endpoints, page docs, table schemas, job docs, config docs
   - ✅ Allowed: external connectors, third-party API clients, field mappings, retry strategies, auth configs for external systems
4. 🚫 NEVER ignore --force flag — force 模式下必须重写，禁止判断"已符合规范"跳过

违反以上任何一条 = 立即停止，输出 "BOUNDARY VIOLATION: {which rule}" 并退出。
</critical-rules>

<objective>
Discover and generate integration documentation for a module.

Searches for external system integration points:
1. HTTP clients to third-party APIs (requests, httpx, aiohttp to external domains)
2. Connector/Adapter classes (naming patterns: *Connector, *Adapter, *Client, *Gateway)
3. EDI message handlers (ISA/GS/ST segments, X12 format)
4. ERP integration modules (NetSuite, SAP, QuickBooks SDK usage)
5. Payment gateway integrations (Stripe, PayPal, Braintree)
6. File-based integrations (SFTP uploads, CSV/Excel exports to external systems)

A module with external API calls, connector classes, or third-party SDK usage
ALWAYS has integrations — this skill must find and document them.
</objective>

<process>

## Step 1: Parse arguments

Extract from `$ARGUMENTS`:
- `--module <name>` (required): module name
- `--source <path>` (required): backend source code directory
- `--output <path>` (optional, default: `.planning/ontology`): documentation output directory
- `--force` (optional): re-generate ALL integration docs, overwriting existing content. Without --force, only create new docs for undocumented integrations and skip existing ones.

**🔒 --force 行为定义（强制执行，不可自行跳过）：**

当传入 `--force` 时：
- **必须**重新读取源代码并完整重写每个 integration 文档
- **禁止**判断"现有文件已符合规范"而跳过重写
- **禁止**输出"文件保持现状"然后不做任何修改
- 唯一不覆盖的是 `<!-- manual -->` 标记的段落

Determine PROJECT_ROOT: walk up from `--source` until `pyproject.toml` / `package.json` / `setup.py` found.

## Step 2: Discover external integrations

🚫 扫描范围必须限定在 `--source` 路径内，不得向上扩展到 PROJECT_ROOT 全局扫描。
只有当 `--source` 内没有找到任何集成时，才 fallback 到 PROJECT_ROOT，但 fallback 时必须用 module 名做路径过滤。

### Strategy 1: Connector/Adapter/Client classes
```bash
grep -rn "class.*Connector\|class.*Adapter\|class.*Client\|class.*Gateway\|class.*Integration" "$SOURCE" --include="*.py" --include="*.ts" | grep -v .venv | grep -v node_modules | grep -v __pycache__
```

### Strategy 2: External HTTP calls (excluding internal API calls)
```bash
grep -rn "requests\.\(get\|post\|put\|delete\)\|httpx\.\|aiohttp\.ClientSession\|fetch(" "$SOURCE" --include="*.py" --include="*.ts" | grep -v .venv | grep -v node_modules | grep -v __pycache__ | grep -v "localhost\|127\.0\.0\.1"
```

### Strategy 3: Third-party SDK usage
```bash
grep -rn "stripe\.\|paypal\.\|braintree\.\|netsuite\.\|quickbooks\.\|twilio\.\|sendgrid\.\|aws_client\|boto3\.\|google\.cloud" "$SOURCE" --include="*.py" --include="*.ts" | grep -v .venv | grep -v node_modules | grep -v __pycache__
```

### Strategy 4: EDI/file-based integrations
```bash
grep -rn "ISA\*\|GS\*\|ST\*\|EDI\|edi_\|sftp\|paramiko\|ftplib\|upload_to_\|export_to_" "$SOURCE" --include="*.py" | grep -v .venv | grep -v __pycache__
```

### Strategy 5: Webhook handlers (inbound integrations)
```bash
grep -rn "webhook\|callback_url\|notify_url\|ipn\|/hook/" "$SOURCE" --include="*.py" --include="*.ts" | grep -v .venv | grep -v node_modules
```

### Strategy 6: OAuth/external auth configurations
```bash
grep -rn "oauth\|client_id\|client_secret\|api_key\|api_secret\|EXTERNAL_.*URL\|THIRD_PARTY" "$SOURCE" --include="*.py" --include="*.env*" | grep -v .venv | grep -v __pycache__
```

## Step 3: Classify and generate integration docs

For each discovered integration, determine its type:

| Discovery pattern | Integration type |
|---|---|
| Connector/Adapter/Client class | 连接器（API 集成） |
| Third-party SDK (Stripe, etc.) | SDK 集成 |
| EDI/X12 handlers | EDI 集成 |
| SFTP/file upload/export | 文件集成 |
| Webhook handlers | Webhook（入站集成） |
| OAuth to external system | 认证集成 |

### Integration doc template

```markdown
# {connector_name} — {external_system}集成

> 源文件: `{file_path}`

## 基本信息

| 字段 | 值 |
|------|-----|
| 连接器类型 | {API/SDK/EDI/File/Webhook} |
| 外部系统 | {system_name} |
| 集成方向 | {输出/输入/双向} |
| 模块 | {module} |
| 负责人 | 待补充 |
| 需求来源 | 待补充 |
| 版本 | v1.0 |

## 连接配置

### 认证方式

| 认证类型 | 配置项 | 说明 |
|---------|--------|------|
| {OAuth 2.0/API Key/Basic/Bearer} | {config_items} | {description} |

### 连接参数

| 参数名 | 类型 | 必填 | 默认值 | 环境变量 | 说明 |
|--------|------|------|--------|---------|------|
| {param} | {type} | {是/否} | {default} | {ENV_VAR or —} | {description} |

## 数据格式

### 输出格式（如适用）

{描述输出到外部系统的数据结构}

### 输入格式（如适用）

{描述从外部系统接收的数据结构}

## 字段映射

| 内部字段 | 外部字段 | 类型 | 转换规则 | 说明 |
|---------|---------|------|---------|------|

## 错误处理

| 错误类型 | 说明 | 处理方式 |
|---------|------|---------|
| 连接超时 | 外部系统无响应 | {retry strategy} |
| 认证失败 | 凭据错误或过期 | {handling} |
| 业务错误 | 外部系统返回业务异常 | {handling} |

## 重试策略

| 错误类型 | 是否重试 | 重试次数 | 重试间隔 |
|---------|---------|---------|---------|

## 关联需求

| 需求编号 | 说明 |
|---------|------|
| 待补充 | 待补充 |

## 关联接口

| 接口 | 操作 | 说明 |
|------|------|------|

## 关联数据库

| 表 | 操作 | 说明 |
|-----|------|------|

## 测试点

| 测试点 ID | 测试场景 | 预期结果 |
|-----------|---------|---------|

## 变更记录

| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 影响范围 |
|------|------|--------|--------|--------|--------|
| v1.0 | 待补充 | scaffold 自动生成 | 无（新建） | 从代码反推骨架 | 待补充 |
```

### 写入规则（update-first）

> **Update-first rule:** If the target doc **exists** and is template-compliant (all required `##` sections present, no `待补充` in key fields): READ it first, then use the **Edit tool** to change ONLY the affected sections (update values, insert/update rows, append a `变更记录` row). Preserve ALL unchanged content byte-for-byte, INCLUDING the file's existing line-ending style (CRLF vs LF). Full `Write` only for a brand-new doc, `--force`, or a doc MISSING required template sections (schema migration).
>
> `<!-- manual -->` 标记的段落永不覆盖；模板完整性校验照常执行。

## Step 4: Handle "no integrations" case

**If genuinely no external integrations exist** (no connectors, no third-party SDKs, no external HTTP calls):
- Remove the empty `$OUTPUT/$MODULE/integration/` directory (do not leave empty folders)
- Update MODULE.md "模块资产清单" table: `| 集成文档 | 0（该模块无外部集成） | integration/ |`
- Do NOT leave a bare "0" — always annotate the reason

**IMPORTANT**: A module with external API clients, connector classes, or third-party SDK usage ALWAYS has integrations — do NOT report "0" for such modules.

## Step 5: Report

```
GSD > KB-FILL-INTEGRATION Complete
────────────────────────────────────────────────────────────
Module:            {module}
Integrations found: {N} (connectors: {n1}, SDKs: {n2}, EDI: {n3}, file: {n4}, webhooks: {n5})
Integration docs:  {generated}/{total}
────────────────────────────────────────────────────────────
```

</process>

<notes>
- Safe to re-run: skips existing integration doc files (unless --force is passed)
- With --force: overwrites all integration docs with fresh content from source code
- Recognizes API connectors, third-party SDKs, EDI, file-based, and webhook integrations
- A module with external HTTP calls or connector classes MUST report integrations
- Integration docs feed into the knowledge graph as "integration" type nodes
</notes>
