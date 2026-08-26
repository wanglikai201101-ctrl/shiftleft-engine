# Sub-skill: Start Application (三路径)

## Purpose

启动应用并确保健康检查通过。先进行运行时环境探测，再根据探测结果选择最优启动路径。

## Input (provided by orchestrator)

- `source` — 项目根目录
- `module` — 模块名
- `backend_dir` — 后端目录（可能等于 source）
- `frontend_dir` — 前端目录（可能为空）
- `backend_port` — 后端端口
- `frontend_port` — 前端端口
- `compose_path` — docker-compose 路径（如果检测到）
- `dockerfile_path` — Dockerfile 路径（如果检测到）
- `language` — 检测到的语言
- `framework` — 检测到的框架
- `db_url` — 数据库连接串
- `changed_files` — git diff 变更文件列表（用于 pre-build 依赖检查）

## Execution

```
Step 0: 运行时环境探测 → RUNTIME-PROFILE (via RUNTIME-DETECT.md)
    ↓
Pre-build: 依赖检查（从变更文件扫描新 import）
    ↓
路径选择（基于 RUNTIME-PROFILE.CHOSEN_PATH）
    ↓
路径 A: Docker 方式（Docker 可用时优先）
  ↓ 构建失败 (retry > 2) 或 Docker 不可用
路径 B: 本地 dev server（运行时可用）
  ↓ 启动失败
路径 C: STOP + 诊断
```

---

### Step 0: Runtime Detection

**Read:** `sub-skills/RUNTIME-DETECT.md` — 执行完整的运行时环境探测。

执行 RUNTIME-DETECT.md 中定义的所有检测步骤（1-7），获得 RUNTIME-PROFILE 变量集合。

关键输出变量：
- `CHOSEN_PATH` — A | B | C（决定下面走哪条路径）
- `DOCKER_RUNNING` / `DOCKER_COMPOSE_CMD` — 路径 A 使用
- `PKG_MANAGER` / `PY_PKG_MANAGER` / `PY_ENV_TYPE` — 路径 B 使用
- `OS_TYPE` — Windows 适配使用

🚫 如果 CHOSEN_PATH = "C"，直接跳到路径 C，不要尝试路径 A 或 B。
🚫 如果 Docker 未安装或未运行，不要尝试路径 A，即使存在 Dockerfile。

---

### Pre-build: 依赖增量检查

**目的：** build 之前主动补齐新包，避免构建失败重试。只扫描 git diff 变更文件，不全量扫描。

#### Python 项目:
```bash
# 从变更文件提取新增 import
git diff {since} HEAD -- {changed_py_files} | grep "^+" | grep -E "^\\+\\s*(import|from)" \
  | sed 's/^+\s*//' | awk '{print $2}' | cut -d. -f1 | sort -u > /tmp/new_imports.txt

# 对比已有依赖
pip freeze | awk -F= '{print tolower($1)}' > /tmp/installed.txt
cat requirements*.txt 2>/dev/null | grep -v "^#" | awk -F[=<>!] '{print tolower($1)}' >> /tmp/installed.txt

# 找出缺失的（排除标准库）
python3 -c "
import sys, importlib
stdlib = set(sys.stdlib_module_names) if hasattr(sys, 'stdlib_module_names') else set()
installed = set(open('/tmp/installed.txt').read().split())
for mod in open('/tmp/new_imports.txt').read().split():
    if mod.lower() not in stdlib and mod.lower() not in installed:
        print(mod)
" > /tmp/missing_deps.txt
```

如果 `/tmp/missing_deps.txt` 非空:
```bash
# 追加到 requirements.txt
cat /tmp/missing_deps.txt >> requirements.txt
echo "Pre-build: added $(wc -l < /tmp/missing_deps.txt) missing packages"
```

#### Node.js 项目:
```bash
# 从变更文件提取新增 import/require
git diff {since} HEAD -- {changed_js_files} | grep "^+" \
  | grep -E "(import .+ from ['\"]|require\(['\"])" \
  | sed -E "s/.*from ['\"]([^'\"]+)['\"].*/\1/; s/.*require\(['\"]([^'\"]+)['\"].*/\1/" \
  | grep -v "^\." | cut -d/ -f1-2 | sort -u > /tmp/new_imports.txt

# 对比 package.json dependencies
node -e "
const pkg = require('./package.json');
const deps = {...(pkg.dependencies||{}), ...(pkg.devDependencies||{})};
console.log(Object.keys(deps).join('\n'));
" > /tmp/installed.txt 2>/dev/null

# 找缺失的（排除 node 内置模块和相对路径）
comm -23 /tmp/new_imports.txt /tmp/installed.txt > /tmp/missing_deps.txt
```

如果 `/tmp/missing_deps.txt` 非空:
```bash
# 安装缺失的包
xargs npm install --save < /tmp/missing_deps.txt
echo "Pre-build: installed $(wc -l < /tmp/missing_deps.txt) missing packages"
```

#### 检查结果:
```
Pre-build dependency check:
  Changed files scanned: {N}
  New imports found: {N}
  Missing packages: {N}
  Auto-installed: {list|none}
```

---

### 路径 A: Docker 方式

🚫 只有 `DOCKER_RUNNING = true` 时才进入此路径。使用 `DOCKER_COMPOSE_CMD` 变量（不要硬编码 `docker-compose`）。

#### A1: 有 docker-compose → 直接用
```bash
cd {source}
$DOCKER_COMPOSE_CMD -f {compose_path} up -d --build
```

#### A2: 只有 Dockerfile → build and run
```bash
docker build -t {module}-test -f {dockerfile_path} {source}
docker run -d --name {module}-test -p {port}:{port} {module}-test
```

#### A3: 无 Docker 配置但 Docker 可用 → 生成 docker-compose.yml

检测前后端结构：
```bash
ls {source}/frontend/package.json 2>/dev/null || \
ls {source}/web/package.json 2>/dev/null || \
ls {source}/client/package.json 2>/dev/null
```

如果是前后端同目录 → 生成 `docker-compose.test.yml`:
```yaml
version: '3.8'
services:
  backend:
    build:
      context: ./{backend_dir}
    ports:
      - "{backend_port}:{backend_port}"
    environment:
      - DATABASE_URL={db_url}
    depends_on:
      - db

  frontend:
    build:
      context: ./{frontend_dir}
    ports:
      - "{frontend_port}:{frontend_port}"
    environment:
      - VITE_API_URL=http://backend:{backend_port}

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_PASSWORD=testpass
      - POSTGRES_DB={module}_test
    ports:
      - "5432:5432"
```

同时为缺失 Dockerfile 的 service 生成：

**Node.js:**
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build 2>/dev/null || true
EXPOSE {port}
CMD ["npm", "start"]
```

**Python:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements*.txt ./
RUN pip install -r requirements.txt
COPY . .
EXPOSE {port}
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{port}"]
```

执行:
```bash
$DOCKER_COMPOSE_CMD -f docker-compose.test.yml up -d --build
```

#### A4: 构建失败 → 自动修复（最多 2 次重试）

读取错误日志：
```bash
$DOCKER_COMPOSE_CMD -f {compose_file} logs --tail=50 2>&1 || docker logs {module}-test --tail=50 2>&1
```

常见失败 + 自动修复：

| 错误信号 | 原因 | 修复方式 |
|---------|------|---------|
| `ModuleNotFoundError` / `No module named` | Python 缺包 | 从 import 推导，追加到 requirements.txt |
| `Cannot find module` / `MODULE_NOT_FOUND` | Node 缺包 | 从 import/require 推导，`npm install {pkg}` |
| `Could not find a version that satisfies` | 包版本冲突 | 放宽版本约束或换 base image |
| `EACCES: permission denied` | 权限问题 | Dockerfile 加 `RUN chmod` 或 `USER node` |
| `node: not found` / `python3: not found` | base image 不对 | 换更完整的 base image |
| `COPY failed: file not found` | 路径错误 | 修正 COPY 的 context 相对路径 |
| `port already in use` | 端口冲突 | 换可用端口 |
| `connection refused` (DB) | DB 没启动 | 加 depends_on + healthcheck wait |

修复流程:
1. 解析错误日志 → 匹配上表
2. 修改 Dockerfile / docker-compose / requirements / package.json
3. 重试 build (retry_count += 1)
4. retry_count > 2 → fallback 路径 B

---

### 路径 B: 本地 dev server

🚫 只有 RUNTIME-PROFILE 确认对应运行时可用时才进入此路径。

#### B1: Python 项目启动

```bash
# 激活/创建虚拟环境
if [ "$PY_ENV_TYPE" = "venv" ] || [ "$PY_ENV_TYPE" = "active-venv" ]; then
  # 已有虚拟环境，激活
  [ -n "$PY_ACTIVATE" ] && source "$PY_ACTIVATE"
elif [ "$PY_PKG_MANAGER" = "uv" ]; then
  # uv 管理的项目
  uv venv 2>/dev/null || true
  source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null
elif [ "$PY_PKG_MANAGER" = "poetry" ]; then
  poetry install
elif [ "$PY_PKG_MANAGER" = "pipenv" ]; then
  pipenv install
else
  # 创建新 venv
  $PYTHON_CMD -m venv .venv
  source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null
fi

# 安装依赖（根据包管理器）
case "$PY_PKG_MANAGER" in
  uv)      uv pip install -r requirements.txt 2>/dev/null; uv pip install -e . 2>/dev/null ;;
  poetry)  poetry install ;;
  pipenv)  pipenv install ;;
  pip)     pip install -r requirements.txt 2>/dev/null; pip install -e . 2>/dev/null ;;
esac

# 启动服务（根据框架）
case "$framework" in
  fastapi|starlette)  uvicorn main:app --host 0.0.0.0 --port {port} & ;;
  flask)              flask run --host 0.0.0.0 --port {port} & ;;
  django)             python manage.py runserver 0.0.0.0:{port} & ;;
  *)                  # 尝试通用启动
                      if grep -q "uvicorn" requirements.txt 2>/dev/null; then
                        uvicorn main:app --host 0.0.0.0 --port {port} &
                      elif [ -f "manage.py" ]; then
                        python manage.py runserver 0.0.0.0:{port} &
                      fi ;;
esac
```

#### B2: Node.js 项目启动

```bash
cd {backend_dir}

# 安装依赖（使用检测到的包管理器）
case "$PKG_MANAGER" in
  pnpm)  pnpm install ;;
  yarn)  yarn install ;;
  npm)   npm install ;;
esac

# 启动服务（检测 scripts）
START_SCRIPT=""
if node -e "const p=require('./package.json'); process.exit(p.scripts && p.scripts.dev ? 0 : 1)" 2>/dev/null; then
  START_SCRIPT="dev"
elif node -e "const p=require('./package.json'); process.exit(p.scripts && p.scripts.start ? 0 : 1)" 2>/dev/null; then
  START_SCRIPT="start"
elif node -e "const p=require('./package.json'); process.exit(p.scripts && p.scripts.serve ? 0 : 1)" 2>/dev/null; then
  START_SCRIPT="serve"
fi

if [ -n "$START_SCRIPT" ]; then
  case "$PKG_MANAGER" in
    pnpm)  pnpm run $START_SCRIPT & ;;
    yarn)  yarn $START_SCRIPT & ;;
    npm)   npm run $START_SCRIPT & ;;
  esac
fi
```

#### B3: Go 项目启动

```bash
if [ "$GO_AVAILABLE" = "true" ] && [ -f "{source}/go.mod" ]; then
  cd {source}
  go run . --port {port} 2>/dev/null || go run . &
fi
```

#### B4: Java 项目启动

```bash
if [ "$JAVA_AVAILABLE" = "true" ]; then
  cd {source}
  case "$JAVA_BUILD" in
    maven)   mvn spring-boot:run -Dserver.port={port} & ;;
    gradle)  ./gradlew bootRun --args="--server.port={port}" & ;;
  esac
fi
```

#### B5: 前端单独启动（如果有独立前端目录）

```bash
if [ -n "{frontend_dir}" ] && [ -f "{frontend_dir}/package.json" ]; then
  cd {frontend_dir}
  
  # 检测前端包管理器（可能与后端不同）
  FE_PKG=""
  if [ -f "pnpm-lock.yaml" ] && command -v pnpm &>/dev/null; then FE_PKG="pnpm"
  elif [ -f "yarn.lock" ] && command -v yarn &>/dev/null; then FE_PKG="yarn"
  else FE_PKG="npm"
  fi
  
  $FE_PKG install
  $FE_PKG run dev &
fi
```

#### B-failure: 启动失败处理

| 错误信号 | 修复方式 |
|---------|---------|
| npm/pnpm install 失败 | 尝试 `--legacy-peer-deps` (npm) 或清除 node_modules 重试 |
| pip install 失败 | 检查是否需要系统依赖 (gcc, libpq-dev 等)；尝试 `--break-system-packages` (新 pip) |
| 端口被占 | `lsof -i :{port}` (Linux/macOS) 或 `netstat -ano \| findstr :{port}` (Windows) 找占用进程，换端口 |
| DB 连接失败 | 检查 .env DATABASE_URL，提示启动 DB 或使用 SQLite fallback |
| Permission denied | Windows: 检查防火墙；Linux/macOS: `chmod +x` 或 `sudo` |
| venv 激活失败 (Windows) | 检查执行策略: `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |

路径 B 也失败 → 进入路径 C。

---

### 路径 C: 无法启动 → STOP

```
❌ Application could not be started.

Attempted:
  路径 A (Docker): {error_summary}
  路径 B (Local):  {error_summary}

Diagnosis:
  - {specific issue}
  - {suggested fix}

Manual action needed:
  - {what user should do}

修复后重跑（开放发布集命令）:
  /gsd-kb-fill --module {module} --source {source} --output docs/kb
  /gsd-kb-gen-tests-api --module {module} --output docs/kb
  /gsd-kb-gen-tests-e2e --module {module} --output docs/kb
  /gsd-kb-gen-tests-ui  --module {module} --output docs/kb
```

---

### Healthcheck (所有路径共用)

Poll until healthy (max 90s, 3s intervals):
```bash
for i in $(seq 1 30); do
  for path in /health /api/health /healthz /api/v1/health /ping /; do
    status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:{port}${path}" 2>/dev/null)
    [ "$status" = "200" ] && break 2
  done
  sleep 3
done
```

Frontend check:
```bash
curl -s -o /dev/null -w "%{http_code}" "http://localhost:{frontend_port}/" 2>/dev/null
```

🔒 FRONTEND DEEP READINESS CHECK (MANDATORY after route returns 200):

After the frontend route returns HTTP 200/302, verify static assets are actually serving:

```bash
# 1. Fetch HTML and extract JS/CSS resource URLs
RESOURCES=$(curl -s "http://localhost:{frontend_port}/" | grep -oE '(src|href)="(/[^"]+\.(js|css))"' | grep -oE '/[^"]+' | head -5)

# 2. Verify each resource returns 200
DEEP_OK=true
for res in $RESOURCES; do
  res_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:{frontend_port}${res}")
  if [ "$res_status" != "200" ]; then
    echo "[healthcheck] DEEP CHECK FAILED: $res → HTTP $res_status"
    DEEP_OK=false
  fi
done

# 3. If any resource 404, wait 10s and retry (max 3 retries — dev server may still be compiling)
RETRY=0
while [ "$DEEP_OK" = "false" ] && [ $RETRY -lt 3 ]; do
  RETRY=$((RETRY + 1))
  echo "[healthcheck] Waiting 10s for frontend compilation (retry $RETRY/3)..."
  sleep 10
  DEEP_OK=true
  for res in $RESOURCES; do
    res_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:{frontend_port}${res}")
    if [ "$res_status" != "200" ]; then
      DEEP_OK=false
    fi
  done
done

# 4. Final verdict
if [ "$DEEP_OK" = "false" ]; then
  echo "❌ Frontend deep check FAILED after 3 retries — JS/CSS chunks not serving"
  # Report as unhealthy
fi
```

Rules:
- frontend_healthy = true ONLY when BOTH: route returns 200 AND at least 1 JS resource returns 200
- If no JS resources found in HTML (static site / SSR without client JS) → skip deep check
- This prevents false-positive health when dev server serves HTML shell but chunks are still compiling

## Output

```
runtime_profile:
  os: {OS_TYPE}
  docker: {DOCKER_RUNNING} (compose_cmd: {DOCKER_COMPOSE_CMD|none})
  node: {NODE_VERSION|none} (pkg: {PKG_MANAGER})
  python: {PYTHON_VERSION|none} (env: {PY_ENV_TYPE|none}, pkg: {PY_PKG_MANAGER})
  go: {GO_VERSION|none}
  java: {JAVA_VERSION|none}

path_selected: {A|B|C}
path_reason: {Docker available + compose exists | Node runtime + pnpm detected | ...}
started_via: {compose|dockerfile|generated-compose|local-dev-server-{PKG_MANAGER}}
backend_url: http://localhost:{backend_port}
frontend_url: http://localhost:{frontend_port}
health_endpoint: {path}
retries: {0|1|2}
```
