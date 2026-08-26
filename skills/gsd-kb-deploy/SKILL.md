---
name: gsd-kb-deploy
description: "Deploy app locally (Docker) or connect to remote env — create test account, auto-generate ENV-CONFIG"
argument-hint: "--module <name> {--source <path> | --connect --url <url> --user <email> --pass <pwd>} [--dry-run]"
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

1. 🚫 NEVER skip healthcheck — 应用必须响应 200 才能进入下一步
2. 🚫 NEVER hardcode port — 必须从 docker-compose/Dockerfile/env 中解析
3. 🚫 NEVER guess registration API — 必须从代码中找到实际注册路由
4. 🚫 NEVER write raw password to ENV-CONFIG — 密码字段使用 `{{AUTH_PASSWORD}}` 占位，实际值存在 ENV-CONFIG.json
5. 🚫 NEVER skip login verification — 创建账号后必须验证登录能获取 token
6. 🚫 NEVER assume DB schema — SQL fallback 必须先读 ORM/migration 推导表结构
7. 🚫 NEVER expose secrets in LOCATOR-REPORT or logs — 密码只出现在 ENV-CONFIG.json
</critical-rules>

<objective>
Deploy the application locally OR connect to a remote environment, create a dedicated test account,
and auto-generate ENV-CONFIG that downstream skills (gen-tests, regression) consume directly.

**Two modes:**

| Mode | Trigger | What it does |
|------|---------|--------------|
| **Local deploy** | `--source <path>` | Docker build → run → healthcheck → create account → ENV-CONFIG |
| **Remote connect** | `--connect --url <url>` | Probe endpoints → verify/create account → ENV-CONFIG |

After this skill runs, `gsd-kb-gen-tests --type all` can execute
without asking the user for URLs, credentials, or environment details.
</objective>

<process>

## Step 1: Parse arguments and determine mode

Extract from `$ARGUMENTS`:

**Common args:**
- `--module <name>` (required): module name
- `--output <path>` (optional, default: `.planning/ontology`): KB output directory
- `--dry-run` (optional): analyze and report what would be done, don't execute

**Local deploy mode (default):**
- `--source <path>` (required in this mode): project source root
- `--compose <path>` (optional): explicit docker-compose file path
- `--port <N>` (optional): override backend port
- `--skip-docker` (optional): assume app already running, skip docker steps

**Remote connect mode:**
- `--connect` (flag): enable remote connect mode
- `--url <url>` (required in this mode): remote environment base URL
- `--user <email>` (optional): existing account email — skip account creation
- `--pass <pwd>` (optional): existing account password — skip account creation

**Mode detection:**
- Has `--connect` → MODE=connect → jump to Step 6
- Has `--source` → MODE=local → continue to Step 2
- Has both → error, mutually exclusive

```
✅ CHECKPOINT-1: Arguments parsed
   MODULE: {name}
   MODE: {local|connect}
   TARGET: {source_path|remote_url}
```

## Step 2: Detect project type and infrastructure

### 2a: Detect language/framework
```bash
ls {source}/package.json 2>/dev/null     # Node.js
ls {source}/pyproject.toml 2>/dev/null   # Python
ls {source}/requirements.txt 2>/dev/null # Python
ls {source}/pom.xml 2>/dev/null          # Java
ls {source}/go.mod 2>/dev/null           # Go
ls {source}/Cargo.toml 2>/dev/null       # Rust
```

### 2b: Detect existing Docker setup
```bash
find {source} -maxdepth 2 -name "docker-compose*.yml" -o -name "docker-compose*.yaml" | head -5
find {source} -maxdepth 2 -name "Dockerfile*" | head -5
```

### 2c: Detect .env files and extract ports/DB config
```bash
find {source} -maxdepth 2 -name ".env*" -not -name ".env.example" | head -5
```

Read .env and docker-compose to extract: backend port, frontend port, DB connection, seed credentials.

```
✅ CHECKPOINT-2: Project detected
   Language: {node|python|java|go|rust}
   Framework: {express|fastapi|spring|gin|...}
   Docker: {compose-exists|dockerfile-only|none}
   Backend port: {N}
   Frontend port: {N|none}
   Database: {postgres|mysql|sqlite|mongo}
```

## Step 3: Pre-start: Kill ports + Probe dependencies

### 3a: Kill existing processes on target ports (MANDATORY)

Before starting any service, ALWAYS kill processes occupying the target ports.
Cross-platform approach:

```bash
kill_port() {
  local port=$1
  echo "[deploy] Killing any process on port $port..."
  if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
    local pid=$(netstat -ano 2>/dev/null | grep ":${port}.*LISTENING" | awk '{print $NF}' | head -1)
    if [ -n "$pid" ] && [ "$pid" != "0" ]; then
      taskkill //F //PID "$pid" 2>/dev/null || true; sleep 2
    fi
  elif [[ "$OSTYPE" == "darwin"* ]]; then
    local pid=$(lsof -ti:$port 2>/dev/null)
    [ -n "$pid" ] && kill -9 $pid 2>/dev/null || true; sleep 1
  else
    local pid=$(lsof -ti:$port 2>/dev/null || ss -tlnp "sport = :$port" 2>/dev/null | grep -oP 'pid=\K\d+' | head -1)
    [ -n "$pid" ] && kill -9 $pid 2>/dev/null || true; sleep 1
  fi
}

kill_port {backend_port}
kill_port {frontend_port}
```

### 3b: Probe external dependencies (MANDATORY)

Read .env/.env.local/.env.development from the backend directory. For each service connection:
- Parse host and port from DATABASE_URL, REDIS_URL, DB_HOST, REDIS_HOST, etc.
- If host is remote (not localhost/127.0.0.1):
  - TCP probe: `nc -z -w 3 {host} {port}` or `curl --connect-timeout 3 telnet://{host}:{port}` or PowerShell TcpClient
  - If unreachable → STOP with:
    ```
    ❌ DEPENDENCY PROBE FAILED: {service} at {host}:{port} is unreachable.
       Source: {env_var} in .env
       Action: Check network/VPN or update .env.
    ```
- If host is localhost/127.0.0.1:
  - Check if a Docker container or local process provides this service
  - If yes → it will be started in Step 4 (include in process-compose)
  - If no → warn but don't block (user may start it manually)

🔒 Rules:
- Do NOT generate Docker containers for services whose .env points to a remote host
- Do NOT skip probing — a failed dependency means the app cannot start correctly
- If no .env exists → skip probing, log warning

### 3c: Validate/regenerate process-compose.yaml

If `{output}/{module}/deploy/process-compose.yaml` exists:
- Check for absolute paths in working_directory → regenerate if found
- Check for Docker commands when .env points to remote services → regenerate if found

If it needs regeneration or doesn't exist → generate per Step 4's process-compose logic.

```
✅ CHECKPOINT-3a: Pre-start checks passed
   Ports killed: {backend_port}, {frontend_port}
   Dependencies probed: {N} services, all reachable
   Process-compose: {valid|regenerated|new}
```

## Step 4: Start application

**Read:** `sub-skills/START-APPLICATION.md`

**Priority path (process-compose — preferred when available):**

Before trying Docker or local dev paths, check for or generate a `process-compose.yaml`:

1. Check if `{output}/{module}/deploy/process-compose.yaml` already exists → use it directly
2. If not, generate one based on Step 2 detection results:

```yaml
# Generate to: {output}/{module}/deploy/process-compose.yaml
version: "0.5"
processes:
  # External services (DB, Redis, etc.) if detected in docker-compose/env
  {external_services_if_any}

  # Backend (if detected)
  backend:
    command: "{backend_start_command}"
    working_directory: "{PROJECT_ROOT}/{backend_dir}"
    readiness_probe:
      http_get:
        host: localhost
        port: {backend_port}
        path: {health_endpoint}
      period_seconds: 3
      failure_threshold: 30

  # Frontend (if detected)
  frontend:
    command: "{frontend_start_command}"
    working_directory: "{PROJECT_ROOT}/{frontend_dir}"
    readiness_probe:
      http_get:
        host: localhost
        port: {frontend_port}
        path: /
      period_seconds: 3
      failure_threshold: 20
    depends_on:
      backend:
        condition: process_healthy
```

3. Start via process-compose:
```bash
# Check if process-compose is installed
if command -v process-compose &>/dev/null; then
  process-compose -f "{output}/{module}/deploy/process-compose.yaml" up -d
else
  # Fallback: parse YAML and start services manually (background processes)
  # Read each process command + working_directory from the YAML, execute in order
fi
```

4. If process-compose start succeeds + healthcheck passes → DONE (skip Docker/local paths below)
5. If process-compose fails → fall through to legacy paths (A/B/C)

**Legacy paths (fallback):**
- Path A: Docker (compose → dockerfile → generate compose) + auto-fix on build failure (max 2 retry)
- Path B: Local dev server (npm/pip/go direct start)
- Path C: STOP + diagnostic report

Healthcheck: poll 90s, try /health /api/health /healthz /ping /

```
✅ CHECKPOINT-4: Application running
   Backend: http://localhost:{backend_port}
   Frontend: http://localhost:{frontend_port}
   Started via: {process-compose|compose|dockerfile|generated-compose|local-dev-server}
   Health endpoint: {path}
   Process-compose file: {output}/{module}/deploy/process-compose.yaml
```

## Step 5: Create test account + verify login

**Read:** `sub-skills/CREATE-ACCOUNT.md`

- Path A: Find registration API in source code → POST to create account
- Path B (fallback): Read ORM/auth model → generate password hash → INSERT SQL

**Detect login_body_field:**
Before attempting login, introspect the login endpoint's request schema to determine the credential field name:
1. Search source code for login schema/model (e.g. Pydantic `BaseModel`, DTO class, Zod schema) that the login endpoint consumes
2. Identify the non-password field name (typically `email`, `username`, or `phone`)
3. If unable to determine from code → try login with `"email"` first; if 422/400, retry with `"username"`
4. Store the detected field name as `login_body_field` for ENV-CONFIG generation

Then verify login:
```bash
curl -X POST http://localhost:{port}/{login_path} \
  -H "Content-Type: application/json" \
  -d '{"{login_body_field}":"qa_autotest@test.local","password":"{{TEST_ACCOUNT_PASSWORD}}"}'
```

Extract token from response. Must succeed before continuing.

```
✅ CHECKPOINT-5: Account created + login verified
   Method: {api_register|sql_fallback}
   Login endpoint: {path}
   Login body field: {email|username|phone}
   Auth method: {bearer|cookie|session}
   Role: {admin|user} (elevated: {true|false}, via: {sql|admin_api|registration_param|failed})
```

## Step 6: Remote Connect Flow (--connect mode only)

**Read:** `sub-skills/REMOTE-CONNECT.md`

Skips Steps 2-4 entirely. Probes remote URL for health/login/register endpoints.
Uses provided credentials or attempts registration on remote.
Generates ENV-CONFIG with `deploy_method: "remote-connect"`.

```
✅ CHECKPOINT-6: Remote connected
   Remote URL: {url}
   Login: verified
   Account: {provided|registered}
```

## Step 7: Generate ENV-CONFIG.json

### 7a: Auto-detect i18n (deterministic — no AI guessing)

Resolve the frontend source root (`{frontend_root}`), then:

```bash
# 1. Locate i18n init file (commonly app/i18n/index.ts or src/i18n/index.ts)
I18N_INIT=$(find {frontend_root} -path "*/i18n/index.ts" -not -path "*/node_modules/*" | head -1)
# 2. Locate locales dir (relative to frontend root, e.g. app/i18n/locales)
LOCALES_DIR=$(find {frontend_root} -type d -path "*/i18n/locales" -not -path "*/node_modules/*" | head -1)
# 3. Extract default locale from INITIAL_LNG / fallbackLng / lng:
DEFAULT_LOCALE=$(grep -oE "(INITIAL_LNG|fallbackLng|lng:)[^']*'[^']*'" "$I18N_INIT" 2>/dev/null | grep -oE "'[^']*'" | head -1 | tr -d "'")
```

- Fill `i18n.default_locale` from `DEFAULT_LOCALE`, `i18n.locales_dir` from `LOCALES_DIR` (relative from the frontend source root to the locales dir).
- If detection fails → default `default_locale` to `"en"` and record the fallback in `i18n.notes`.

### 7b: Write ENV-CONFIG.json

Write to `{output}/{module}/tests/ENV-CONFIG.json`:

```json
{
  "_meta": {
    "generated_by": "gsd-kb-deploy",
    "generated_at": "{TODAY}",
    "module": "{module}",
    "deploy_method": "{compose|dockerfile|generated|local-dev|remote-connect}",
    "account_method": "{api_register|sql_fallback|provided}"
  },
  "environment": {
    "backend_url": "{backend_url}",
    "frontend_url": "{frontend_url}",
    "frontend_login_path": "{login_path}",
    "health_endpoint": "{health_path}",
    "api_prefix": "{/api/v1|/api|/}"
  },
  "auth": {
    "method": "{bearer|cookie|session}",
    "system": "{project_name from source directory basename or PROJECT.md}",
    "role": "admin",
    "username": "{email}",
    "password": "{password}",
    "login_endpoint": "{login_path}",
    "login_body_field": "{email|username|phone}",
    "token_field": "{response.token|response.data.token|...}",
    "register_endpoint": "{register_path|null}"
  },
  "executor": {
    "url": "{{EXECUTOR_URL}}",
    "token": "{{EXECUTOR_TOKEN}}",
    "control_url": "{{EXECUTOR_CONTROL_URL}}"
  },
  "i18n": {
    "default_locale": "{default_locale}",
    "locales_dir": "{locales_dir}",
    "detection_strategy": "auto",
    "detection_hints": ["app/i18n/index.ts", "INITIAL_LNG", "fallbackLng"],
    "notes": "{i18n init facts — INITIAL_LNG/fallbackLng values, or 'defaulted to en'}"
  },
  "database": {
    "type": "{postgres|mysql|sqlite|mongo|remote}",
    "container": "{db_container_name|null}",
    "connection": "{connection_string_without_password|null}"
  }
}
```

> ⚠️ `executor.url` / `executor.control_url` / `executor.token` 为参数化占位符，写入 ENV-CONFIG.json 前替换为实际执行引擎端点与 token（端点与 token 由部署配置注入，不在此处硬编码）。

**Compatibility guarantee:** This format is what `gsd-kb-gen-tests-ui/api/e2e` expect.

```
✅ CHECKPOINT-7: ENV-CONFIG generated
   Path: {output}/{module}/tests/ENV-CONFIG.json
   Backend: {url}
   Frontend: {url}
   Auth: {method} via {login_endpoint}
   i18n: {default_locale} (locales_dir: {locales_dir})
   Executor: {executor.url}
```

## Step 8: Generate DEPLOY-REPORT.md

Write to `{output}/{module}/DEPLOY-REPORT.md` with deployment summary, endpoints discovered,
test account details, and next-step commands.

```
✅ DEPLOY COMPLETE
   DEPLOY-REPORT: {output}/{module}/DEPLOY-REPORT.md
   ENV-CONFIG: {output}/{module}/tests/ENV-CONFIG.json
   Ready for: gen-tests, regression, enforce-locators
```

</process>

<notes>
- Safe to re-run: checks if account exists before creating, updates ENV-CONFIG idempotently
- Two modes: `--source` (local Docker/dev) and `--connect --url` (remote probe)
- --skip-docker for when local app is already running
- Sub-skills contain detailed logic; this file is orchestration only
- ENV-CONFIG.json is the contract between deploy and all test-generation skills
- If frontend and backend are same service (SSR), frontend_url = backend_url
- Docker containers named `{module}-test` for easy cleanup
- Remote mode has no DB access — SQL fallback unavailable
</notes>
