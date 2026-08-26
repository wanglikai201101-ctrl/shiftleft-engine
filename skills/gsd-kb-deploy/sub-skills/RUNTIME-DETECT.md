# Sub-skill: Runtime Detection (运行时环境探测)

## Purpose

在任何启动/构建操作之前，探测本机可用的运行时环境，输出 RUNTIME-PROFILE 供路径选择决策使用。

此 sub-skill 可被多个 skill 复用：
- `gsd-kb-deploy` (START-APPLICATION) — 决定 Docker vs 本地启动
- `gsd-kb-branch` — 无直接依赖但可作为诊断参考

## Input

- `source` — 项目根目录
- `backend_dir` — 后端目录（可能等于 source）
- `language` — 已检测到的语言（可选，用于加速判断）
- `compose_path` — docker-compose 路径（如果检测到）
- `dockerfile_path` — Dockerfile 路径（如果检测到）

## Output: RUNTIME-PROFILE

探测结果作为 shell 变量集合传递给调用方。关键变量：

```
OS_TYPE              — windows | macos | linux
DOCKER_INSTALLED     — true | false
DOCKER_RUNNING       — true | false
DOCKER_VERSION       — 版本字符串
DOCKER_COMPOSE_CMD   — "docker compose" | "docker-compose" | ""
NODE_AVAILABLE       — true | false
NODE_VERSION         — 版本字符串
PKG_MANAGER          — pnpm | yarn | npm | ""
PKG_MANAGER_VERSION  — 版本字符串
PYTHON_AVAILABLE     — true | false
PYTHON_CMD           — python3 | python | ""
PYTHON_VERSION       — 版本字符串
PY_ENV_TYPE          — venv | active-venv | conda | ""
PY_ACTIVATE          — activate 脚本路径
PY_PKG_MANAGER       — uv | poetry | pipenv | pip
GO_AVAILABLE         — true | false
GO_VERSION           — 版本字符串
JAVA_AVAILABLE       — true | false
JAVA_VERSION         — 版本字符串
JAVA_BUILD           — maven | gradle | ""
RUST_AVAILABLE       — true | false
CHOSEN_PATH          — A | B | C
```

## Execution

### 1. OS 检测

```bash
OS_TYPE=""
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ -n "$WINDIR" ]]; then
  OS_TYPE="windows"
elif [[ "$OSTYPE" == "darwin"* ]]; then
  OS_TYPE="macos"
else
  OS_TYPE="linux"
fi
```

### 2. Docker 检测

```bash
DOCKER_INSTALLED=false
DOCKER_RUNNING=false
DOCKER_COMPOSE_CMD=""

if command -v docker &>/dev/null; then
  DOCKER_INSTALLED=true
  DOCKER_VERSION=$(docker --version 2>/dev/null | head -1)
  
  # 检测 daemon 是否运行（不能只看 CLI 存在）
  if docker info &>/dev/null; then
    DOCKER_RUNNING=true
  fi
  
  # 检测 compose 命令形式
  if docker compose version &>/dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
  elif command -v docker-compose &>/dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
  fi
fi
```

### 3. Node.js 运行时检测

```bash
NODE_AVAILABLE=false
NODE_VERSION=""
PKG_MANAGER=""
PKG_MANAGER_VERSION=""

if command -v node &>/dev/null; then
  NODE_AVAILABLE=true
  NODE_VERSION=$(node --version 2>/dev/null)
fi

# 包管理器检测（按锁文件优先级）
if [ -f "{source}/pnpm-lock.yaml" ] || [ -f "{backend_dir}/pnpm-lock.yaml" ]; then
  if command -v pnpm &>/dev/null; then
    PKG_MANAGER="pnpm"
    PKG_MANAGER_VERSION=$(pnpm --version 2>/dev/null)
  fi
elif [ -f "{source}/yarn.lock" ] || [ -f "{backend_dir}/yarn.lock" ]; then
  if command -v yarn &>/dev/null; then
    PKG_MANAGER="yarn"
    PKG_MANAGER_VERSION=$(yarn --version 2>/dev/null)
  fi
elif [ -f "{source}/package-lock.json" ] || [ -f "{backend_dir}/package-lock.json" ]; then
  if command -v npm &>/dev/null; then
    PKG_MANAGER="npm"
    PKG_MANAGER_VERSION=$(npm --version 2>/dev/null)
  fi
else
  # 无锁文件，按可用性 fallback
  if command -v pnpm &>/dev/null; then PKG_MANAGER="pnpm"
  elif command -v yarn &>/dev/null; then PKG_MANAGER="yarn"
  elif command -v npm &>/dev/null; then PKG_MANAGER="npm"
  fi
fi

# 检测 engines 约束
REQUIRED_NODE="any"
if [ -f "{source}/package.json" ] && [ "$NODE_AVAILABLE" = "true" ]; then
  REQUIRED_NODE=$(node -e "const p=require('./{source}/package.json'); console.log((p.engines||{}).node||'any')" 2>/dev/null)
fi
```

### 4. Python 运行时检测

```bash
PYTHON_AVAILABLE=false
PYTHON_CMD=""
PYTHON_VERSION=""
PY_ENV_TYPE=""
PY_ACTIVATE=""
PY_PKG_MANAGER=""

# 检测 python 命令
if command -v python3 &>/dev/null; then
  PYTHON_AVAILABLE=true
  PYTHON_CMD="python3"
  PYTHON_VERSION=$(python3 --version 2>/dev/null)
elif command -v python &>/dev/null; then
  PYTHON_AVAILABLE=true
  PYTHON_CMD="python"
  PYTHON_VERSION=$(python --version 2>/dev/null)
fi

# 检测虚拟环境（已存在）
if [ -d "{source}/.venv" ]; then
  PY_ENV_TYPE="venv"
  PY_ACTIVATE="{source}/.venv/bin/activate"
elif [ -d "{source}/venv" ]; then
  PY_ENV_TYPE="venv"
  PY_ACTIVATE="{source}/venv/bin/activate"
elif [ -n "$VIRTUAL_ENV" ]; then
  PY_ENV_TYPE="active-venv"
  PY_ACTIVATE=""
elif [ -n "$CONDA_DEFAULT_ENV" ]; then
  PY_ENV_TYPE="conda"
fi

# Windows 下 activate 路径适配
if [ "$OS_TYPE" = "windows" ] && [ "$PY_ENV_TYPE" = "venv" ]; then
  PY_ACTIVATE="${PY_ACTIVATE//bin/Scripts}"
fi

# 检测包管理器偏好
if [ -f "{source}/uv.lock" ] || { [ -f "{source}/pyproject.toml" ] && command -v uv &>/dev/null; }; then
  PY_PKG_MANAGER="uv"
elif [ -f "{source}/Pipfile" ] && command -v pipenv &>/dev/null; then
  PY_PKG_MANAGER="pipenv"
elif [ -f "{source}/poetry.lock" ] && command -v poetry &>/dev/null; then
  PY_PKG_MANAGER="poetry"
else
  PY_PKG_MANAGER="pip"
fi
```

### 5. Go / Java / Rust 检测

```bash
GO_AVAILABLE=false
JAVA_AVAILABLE=false
RUST_AVAILABLE=false
GO_VERSION=""
JAVA_VERSION=""
JAVA_BUILD=""

if command -v go &>/dev/null; then
  GO_AVAILABLE=true
  GO_VERSION=$(go version 2>/dev/null)
fi

if command -v java &>/dev/null; then
  JAVA_AVAILABLE=true
  JAVA_VERSION=$(java -version 2>&1 | head -1)
  if command -v mvn &>/dev/null; then JAVA_BUILD="maven"
  elif command -v gradle &>/dev/null; then JAVA_BUILD="gradle"
  fi
fi

if command -v cargo &>/dev/null; then
  RUST_AVAILABLE=true
fi
```

### 6. 路径选择决策

```bash
CHOSEN_PATH=""
PATH_REASON=""

if [ "$DOCKER_RUNNING" = "true" ] && { [ -n "$compose_path" ] || [ -n "$dockerfile_path" ]; }; then
  CHOSEN_PATH="A"
  PATH_REASON="Docker running + Docker config exists"
elif [ "$DOCKER_RUNNING" = "true" ] && { [ "$language" = "python" ] || [ "$language" = "node" ]; }; then
  CHOSEN_PATH="A"
  PATH_REASON="Docker running + known language (can generate compose)"
elif [ "$language" = "node" ] && [ "$NODE_AVAILABLE" = "true" ] && [ -n "$PKG_MANAGER" ]; then
  CHOSEN_PATH="B"
  PATH_REASON="Node runtime available ($PKG_MANAGER)"
elif [ "$language" = "python" ] && [ "$PYTHON_AVAILABLE" = "true" ]; then
  CHOSEN_PATH="B"
  PATH_REASON="Python runtime available ($PY_PKG_MANAGER, env: ${PY_ENV_TYPE:-none})"
elif [ "$language" = "go" ] && [ "$GO_AVAILABLE" = "true" ]; then
  CHOSEN_PATH="B"
  PATH_REASON="Go runtime available"
elif [ "$language" = "java" ] && [ "$JAVA_AVAILABLE" = "true" ]; then
  CHOSEN_PATH="B"
  PATH_REASON="Java runtime available ($JAVA_BUILD)"
else
  CHOSEN_PATH="C"
  PATH_REASON="No usable runtime detected"
fi
```

### 7. Summary Output

```
Runtime Detection Complete:
─────────────────────────────────────────────
  OS:           {OS_TYPE}
  Docker:       {DOCKER_INSTALLED} (daemon: {DOCKER_RUNNING}, compose: {DOCKER_COMPOSE_CMD|none})
  Node.js:      {NODE_VERSION|not installed} (pkg: {PKG_MANAGER} {PKG_MANAGER_VERSION})
  Python:       {PYTHON_VERSION|not installed} (env: {PY_ENV_TYPE|none}, pkg: {PY_PKG_MANAGER})
  Go:           {GO_VERSION|not installed}
  Java:         {JAVA_VERSION|not installed} (build: {JAVA_BUILD|none})
  Rust:         {RUST_AVAILABLE}
─────────────────────────────────────────────
  Path selected: {CHOSEN_PATH}
  Reason: {PATH_REASON}
─────────────────────────────────────────────
```

## Rules

🚫 Docker daemon 未运行时，不得选择路径 A，即使 Dockerfile 存在。
🚫 对应语言运行时未安装时，不得选择路径 B。
🚫 不得跳过此探测直接进入启动。
🚫 包管理器必须按锁文件优先，不得盲目默认 npm/pip。
