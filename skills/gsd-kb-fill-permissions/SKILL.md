---
name: gsd-kb-fill-permissions
description: "Permission/auth auto-discovery: role definitions, RBAC/ABAC models, auth middleware chains, permission matrices, multi-tenancy"
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

1. 🚫 NEVER write files outside `$OUTPUT/$MODULE/permissions/` — 禁止写入 apis/, pages/, tech/, graph/, tests/, requirements/, storage/, jobs/, config/, integration/, error-handling/
2. 🚫 NEVER create files with non-standard names — only `{permission-type}.md` format (lowercase, hyphen-separated)
   - ✅ Allowed: `rbac-roles.md`, `route-guards.md`, `tenant-isolation.md`, `auth-endpoints.md`
   - ❌ Forbidden: `SERVICE-*.md`, `_INDEX.md`, `SUMMARY.md`, `README.md`
3. 🚫 NEVER document non-permission concerns — this skill documents PERMISSION/AUTH MECHANISMS only
   - ❌ Forbidden: API business logic, page docs, table schemas, job docs, config docs, error handling
   - ✅ Allowed: role definitions, permission guards, auth middleware, RBAC/ABAC policies, tenant isolation, ownership checks, auth endpoints
4. 🚫 NEVER ignore --force flag — force 模式下必须重写，禁止判断"已符合规范"跳过

违反以上任何一条 = 立即停止，输出 "BOUNDARY VIOLATION: {which rule}" 并退出。
</critical-rules>

<objective>
Discover and generate permission/authorization documentation for a module.

Searches for permission and auth mechanisms:
1. Role definitions (admin/user/viewer/operator enums, role classes)
2. Permission models (RBAC/ABAC/policy-based access control)
3. Auth middleware chains (auth middleware → permission guard → handler)
4. Permission matrices (role × resource × operation mappings)
5. Multi-tenancy/ownership isolation (tenant_id, org_id, owner checks)
6. Auth endpoints (login/register/token-refresh/role-assignment APIs)

A module with role checks, permission decorators, or auth middleware
ALWAYS has permissions — this skill must find and document them.
</objective>

<process>

## Step 1: Parse arguments

Extract from `$ARGUMENTS`:
- `--module <name>` (required): module name
- `--source <path>` (required): backend source code directory
- `--output <path>` (optional, default: `.planning/ontology`): documentation output directory
- `--force` (optional): re-generate ALL permission docs, overwriting existing content. Without --force, only create new docs for undocumented permission mechanisms and skip existing ones.

**🔒 --force 行为定义（强制执行，不可自行跳过）：**

当传入 `--force` 时：
- **必须**重新读取源代码并完整重写每个 permission 文档
- **禁止**判断"现有文件已符合规范"而跳过重写
- **禁止**输出"文件保持现状"然后不做任何修改
- 唯一不覆盖的是 `<!-- manual -->` 标记的段落

Determine PROJECT_ROOT: walk up from `--source` until `pyproject.toml` / `package.json` / `setup.py` found.

## Step 2: Discover permission mechanisms

🚫 扫描范围必须限定在 `--source` 路径内，不得向上扩展到 PROJECT_ROOT 全局扫描。
只有当 `--source` 内没有找到任何权限机制时，才 fallback 到 PROJECT_ROOT，但 fallback 时必须用 module 名做路径过滤。

### Strategy 1: Role definitions (enums, constants, classes)
```bash
grep -rn "class.*Role.*Enum\|class.*Role\|RoleType\|UserRole\|ROLE_\|role_name\|is_admin\|is_superuser\|@roles_required" "$SOURCE" --include="*.py" --include="*.ts" | grep -v .venv | grep -v node_modules | grep -v __pycache__
```

### Strategy 2: Permission decorators and guards
```bash
grep -rn "@require_permission\|@permission_required\|@has_permission\|@authorize\|PermissionGuard\|RolesGuard\|CanActivate\|@UseGuards\|@Roles\|@Permissions\|permission_classes\|IsAuthenticated\|IsAdminUser\|AllowAny" "$SOURCE" --include="*.py" --include="*.ts" | grep -v .venv | grep -v node_modules | grep -v __pycache__
```

### Strategy 3: Auth middleware chains
```bash
grep -rn "auth_middleware\|AuthMiddleware\|JWTAuthentication\|TokenAuthentication\|passport\.\|verify_token\|decode_token\|get_current_user\|Depends(get_current\|security_scheme" "$SOURCE" --include="*.py" --include="*.ts" | grep -v .venv | grep -v node_modules | grep -v __pycache__
```

### Strategy 4: RBAC/ABAC policy models
```bash
grep -rn "class.*Policy\|class.*Permission\|can_access\|has_role\|check_permission\|AbilityBuilder\|defineAbility\|casl\|casbin\|policy_engine\|access_control" "$SOURCE" --include="*.py" --include="*.ts" | grep -v .venv | grep -v node_modules | grep -v __pycache__
```

### Strategy 5: Multi-tenancy and ownership checks
```bash
grep -rn "tenant_id\|org_id\|organization_id\|owner_id\|belongs_to_org\|filter.*tenant\|scope.*organization\|multi_tenant\|current_tenant\|TenantMixin\|owner_check\|is_owner" "$SOURCE" --include="*.py" --include="*.ts" | grep -v .venv | grep -v node_modules | grep -v __pycache__
```

### Strategy 6: Auth endpoints (login/register/token)
```bash
grep -rn "/login\|/register\|/token\|/refresh\|/logout\|/auth/\|/roles\|/permissions\|assign_role\|revoke_role\|create_user\|reset_password" "$SOURCE" --include="*.py" --include="*.ts" | grep -v .venv | grep -v node_modules | grep -v __pycache__ | grep -v "test_\|spec\.\|\.test\."
```

### Strategy 7: Route-level access control (Django/FastAPI/NestJS/Express)
```bash
grep -rn "login_required\|staff_member_required\|user_passes_test\|@app\.before_request\|app\.use.*auth\|router\.use.*auth\|middleware.*auth\|protect.*route" "$SOURCE" --include="*.py" --include="*.ts" --include="*.js" | grep -v .venv | grep -v node_modules | grep -v __pycache__
```

## Step 3: Classify and generate permission docs

### UPDATE-FIRST 增量更新优先（🔒 默认写路径）

**如果目标 permission 文档已存在且符合模板规范**（所有必需 `##` 段齐全，关键字段无 `待补充`）：

1. **先 READ** 目标文档
2. 使用 **Edit 工具** 只修改受影响的段落（更新字段值、插入/更新表格行、追加 `变更记录` 行）
3. **逐字节保留所有未修改内容**，包括文件现有的行尾风格（CRLF vs LF）

**只有以下情况才使用完整 Write（整体重写）：**
- 文档是新建的（brand-new doc，尚不存在）
- 传入了 `--force`
- 文档缺少必需模板段（schema 迁移）

> 模板合规校验仍然生效：编辑后的文档必须保持所有必需 `##` 段齐全，否则判定 REJECTED。

For each discovered mechanism, group by permission domain:

| Discovery pattern | Permission domain |
|---|---|
| Role enum/class | 角色定义 |
| Permission decorators/guards | 权限守卫 |
| Auth middleware chain | 认证中间件 |
| RBAC/ABAC policy model | 访问控制策略 |
| Tenant/org/owner checks | 多租户隔离 |
| Auth endpoints | 认证端点 |
| Route-level access | 路由级权限 |

Group related mechanisms into a single doc per permission domain (e.g., RBAC: roles + guards + middleware = one doc).

### Permission doc template

```markdown
# {permission_domain} — {description}

> 源文件: `{file_path}`

## 基本信息

| 字段 | 值 |
|------|-----|
| 权限域 | {角色定义/权限守卫/认证中间件/访问控制策略/多租户隔离/认证端点} |
| 模型类型 | {RBAC/ABAC/Route-level/Policy-based} |
| 模块 | {module} |
| 负责人 | 待补充 |
| 需求来源 | 待补充 |
| 版本 | v1.0 |

## 角色定义

| 角色 | 标识符 | 说明 | 继承自 |
|------|--------|------|--------|
| {role_name} | {identifier} | {description} | {parent_role or —} |

## 权限矩阵

| 资源 | 操作 | admin | user | viewer | operator |
|------|------|-------|------|--------|----------|
| {resource} | {read/write/delete/manage} | {✓/✗} | {✓/✗} | {✓/✗} | {✓/✗} |

{根据实际代码中的权限检查填写}

## 中间件链

```
Request → [Auth Middleware] → [Token Validation] → [Permission Guard] → [Handler]
                │                     │                     │
                └─ 401 Unauthorized   └─ 401 Invalid Token  └─ 403 Forbidden
```

{描述实际的中间件执行顺序}

## 多租户隔离

| 隔离维度 | 实现方式 | 字段 | 说明 |
|---------|---------|------|------|
| {租户/组织/所有者} | {row-level filter/schema/database} | {tenant_id/org_id/owner_id} | {description} |

## 认证端点

| 端点 | 方法 | 说明 | 需要认证 |
|------|------|------|---------|
| {path} | {GET/POST} | {description} | {是/否} |

## Token 策略

| 字段 | 值 |
|------|-----|
| Token 类型 | {JWT/Session/API Key} |
| 有效期 | {duration} |
| 刷新策略 | {refresh token/sliding window/re-login} |
| 存储方式 | {header/cookie/query param} |

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

## 关联页面

| 页面 | 权限要求 | 说明 |
|------|---------|------|

## 变更记录

| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 影响范围 |
|------|------|--------|--------|--------|--------|
| v1.0 | 待补充 | scaffold 自动生成 | 无（新建） | 从代码反推骨架 | 待补充 |
```

## Step 4: Handle "no permissions" case

**If genuinely no permission mechanisms exist** (no role checks, no auth middleware, no permission decorators):
- Remove the empty `$OUTPUT/$MODULE/permissions/` directory (do not leave empty folders)
- Update MODULE.md "模块资产清单" table: `| 权限文档 | 0（该模块无独立权限机制） | permissions/ |`
- Do NOT leave a bare "0" — always annotate the reason

**IMPORTANT**: A module with auth middleware, role decorators, or permission guards ALWAYS has permissions — do NOT report "0" for such modules.

## Step 5: Report

```
GSD > KB-FILL-PERMISSIONS Complete
────────────────────────────────────────────────────────────
Module:             {module}
Permission domains: {N} (roles: {n1}, guards: {n2}, middleware: {n3}, policies: {n4}, tenancy: {n5}, endpoints: {n6})
Permission docs:    {generated}/{total}
────────────────────────────────────────────────────────────
```

</process>

<notes>
- Safe to re-run: skips existing permission doc files (unless --force is passed)
- With --force: overwrites all permission docs with fresh content from source code
- Groups related mechanisms (roles + guards + middleware) into a single domain doc
- Recognizes RBAC, ABAC, route-level guards, policy engines, and multi-tenancy patterns
- Covers both Python (FastAPI/Django) and TypeScript (NestJS/Express) permission patterns
- A module with auth middleware or role decorators MUST report permissions
- Permission docs feed into the knowledge graph as "permissions" type nodes
</notes>
