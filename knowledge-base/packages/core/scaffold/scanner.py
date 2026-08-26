"""代码反向扫描器：从代码目录扫描接口、表、页面、任务，生成模块文档骨架。

用于存量模块补全文档——无需需求文档，直接从代码反推文档结构。

使用方法：
    from packages.core.scaffold.scanner import CodeScanner
    scanner = CodeScanner("src/billing/")
    result = scanner.scan()
    # result.apis = [ScannedApi(...), ...]
    # result.tables = [ScannedTable(...), ...]
    # result.pages = [ScannedPage(...), ...]
    # result.jobs = [ScannedJob(...), ...]
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class ScannedApi:
    """从代码中扫描到的接口"""
    method: str
    path: str
    function_name: str
    file_path: str
    description: str = ""
    params: List[str] = field(default_factory=list)


@dataclass
class ScannedTable:
    """从代码中扫描到的数据表"""
    table_name: str
    file_path: str
    columns: List[str] = field(default_factory=list)
    source_type: str = "orm"  # "orm" | "migration" | "ddl"


@dataclass
class ScannedPage:
    """从代码中扫描到的前端页面"""
    component_name: str
    file_path: str
    route_path: str = ""
    testids: List[str] = field(default_factory=list)


@dataclass
class ScannedJob:
    """从代码中扫描到的定时任务"""
    job_name: str
    file_path: str
    schedule: str = ""
    description: str = ""


@dataclass
class ScannedRedisKey:
    """从代码中扫描到的 Redis Key"""
    key_pattern: str
    file_path: str
    operation: str = ""  # "set" | "get" | "delete" | "lock" | "cache"
    ttl: str = ""
    data_structure: str = "String"  # "String" | "Hash" | "List" | "Set" | "ZSet"
    description: str = ""


@dataclass
class ScanResult:
    """扫描结果汇总"""
    apis: List[ScannedApi] = field(default_factory=list)
    tables: List[ScannedTable] = field(default_factory=list)
    pages: List[ScannedPage] = field(default_factory=list)
    jobs: List[ScannedJob] = field(default_factory=list)
    redis_keys: List[ScannedRedisKey] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.apis) + len(self.tables) + len(self.pages) + len(self.jobs) + len(self.redis_keys)


# HTTP method decorators/patterns to detect
_ROUTE_DECORATORS = re.compile(
    r'@\w*\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)

# FastAPI router patterns
_ROUTER_DECORATORS = re.compile(
    r'@router\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)

# Flask-style app.route
_FLASK_ROUTE = re.compile(
    r'@\w+\.route\s*\(\s*["\']([^"\']+)["\']'
    r'(?:.*?methods\s*=\s*\[([^\]]+)\])?',
    re.IGNORECASE | re.DOTALL,
)

# SQLAlchemy model patterns
_SQLALCHEMY_TABLE = re.compile(
    r'__tablename__\s*=\s*["\'](\w+)["\']',
)

# Django model Meta
_DJANGO_TABLE = re.compile(
    r'class\s+Meta\s*:.*?db_table\s*=\s*["\'](\w+)["\']',
    re.DOTALL,
)

# Schedule/cron patterns
_SCHEDULE_PATTERNS = [
    re.compile(r'@(?:celery_app|app|celery)\.task', re.IGNORECASE),
    re.compile(r'@shared_task\b', re.IGNORECASE),
    re.compile(r'schedule\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'crontab\s*\(([^)]+)\)', re.IGNORECASE),
    re.compile(r'@scheduler\.\w+\s*\(', re.IGNORECASE),
]

# Vue router
_VUE_ROUTE = re.compile(
    r'path\s*:\s*["\']([^"\']+)["\'].*?component\s*:\s*(\w+)',
    re.DOTALL,
)


class CodeScanner:
    """从代码目录扫描接口、表、页面、任务"""

    def __init__(self, source_dir: str):
        self.source_dir = Path(source_dir)

    def scan(self) -> ScanResult:
        """执行全量扫描"""
        result = ScanResult()

        if not self.source_dir.exists():
            result.errors.append(f"目录不存在: {self.source_dir}")
            return result

        for file_path in self._walk_files():
            try:
                suffix = file_path.suffix.lower()
                if suffix == ".py":
                    self._scan_python(file_path, result)
                elif suffix == ".sql":
                    self._scan_sql(file_path, result)
                elif suffix == ".vue":
                    self._scan_vue(file_path, result)
                elif suffix in (".ts", ".js", ".tsx", ".jsx"):
                    self._scan_js_ts(file_path, result)
            except Exception as e:
                result.errors.append(f"{file_path}: {e}")

        return result

    def _walk_files(self):
        """递归遍历源码文件，跳过常见非源码目录"""
        skip_dirs = {
            "node_modules", ".venv", "__pycache__", ".git",
            "dist", "build", ".output", ".playwright-cli",
            ".next", ".nuxt", ".turbo", "coverage",
        }
        for path in self.source_dir.rglob("*"):
            if path.is_file() and not any(p in path.parts for p in skip_dirs):
                yield path

    def _scan_python(self, file_path: Path, result: ScanResult):
        """扫描 Python 文件：接口路由、ORM 模型、定时任务"""
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        rel_path = str(file_path.relative_to(self.source_dir))

        # 按 (method, path) 去重，防止重叠正则或多文件重复
        seen_apis: set = {(a.method, a.path) for a in result.apis}

        # 扫描路由（FastAPI/Flask 风格）— _ROUTE_DECORATORS 已覆盖 @router.xxx
        for m in _ROUTE_DECORATORS.finditer(content):
            method, path = m.group(1).upper(), m.group(2)
            if (method, path) in seen_apis:
                continue
            seen_apis.add((method, path))
            func_name = self._find_next_function(content, m.end())
            result.apis.append(ScannedApi(
                method=method, path=path,
                function_name=func_name or "unknown",
                file_path=rel_path,
                description=self._extract_docstring(content, m.end()),
            ))

        for m in _FLASK_ROUTE.finditer(content):
            path = m.group(1)
            methods_str = m.group(2)
            methods = ["GET"]
            if methods_str:
                methods = [x.strip().strip("'\"") for x in methods_str.split(",")]
            func_name = self._find_next_function(content, m.end())
            for method in methods:
                if (method.upper(), path) in seen_apis:
                    continue
                seen_apis.add((method.upper(), path))
                result.apis.append(ScannedApi(
                    method=method.upper(), path=path,
                    function_name=func_name or "unknown",
                    file_path=rel_path,
                ))

        # 扫描 ORM 模型
        for m in _SQLALCHEMY_TABLE.finditer(content):
            table_name = m.group(1)
            columns = self._extract_orm_columns(content)
            result.tables.append(ScannedTable(
                table_name=table_name,
                file_path=rel_path,
                columns=columns,
                source_type="orm",
            ))

        for m in _DJANGO_TABLE.finditer(content):
            table_name = m.group(1)
            result.tables.append(ScannedTable(
                table_name=table_name,
                file_path=rel_path,
                source_type="orm",
            ))

        # 扫描定时任务
        for pattern in _SCHEDULE_PATTERNS:
            for m in pattern.finditer(content):
                func_name = self._find_next_function(content, m.end())
                if func_name:
                    schedule = m.group(1) if m.lastindex else ""
                    if not any(j.job_name == func_name for j in result.jobs):
                        result.jobs.append(ScannedJob(
                            job_name=func_name,
                            file_path=rel_path,
                            schedule=schedule,
                            description=self._extract_docstring(content, m.end()),
                        ))

        # 扫描 Redis Key 使用
        self._scan_redis_keys(content, rel_path, result)

    def _scan_sql(self, file_path: Path, result: ScanResult):
        """扫描 SQL 文件：CREATE TABLE"""
        from ..parsers.ddl_parser import DDLParser
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        rel_path = str(file_path.relative_to(self.source_dir))

        parser = DDLParser()
        tables = parser.extract_storage_info(content)
        for table in tables:
            result.tables.append(ScannedTable(
                table_name=table.table_name,
                file_path=rel_path,
                columns=[col.name for col in table.columns],
                source_type="ddl",
            ))

    def _scan_vue(self, file_path: Path, result: ScanResult):
        """扫描 Vue 文件：组件和 data-testid"""
        from ..parsers.vue_parser import VueParser
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        rel_path = str(file_path.relative_to(self.source_dir))

        parser = VueParser()
        page_info = parser.extract_page_info(content)

        result.pages.append(ScannedPage(
            component_name=page_info.component_name or file_path.stem,
            file_path=rel_path,
            testids=[e.testid for e in page_info.elements],
        ))

    def _scan_js_ts(self, file_path: Path, result: ScanResult):
        """扫描 JS/TS 文件：路由定义、Next.js 页面"""
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        rel_path = str(file_path.relative_to(self.source_dir))

        # Next.js App Router: app/**/page.tsx → 页面
        if self._is_nextjs_page(file_path):
            route_path = self._derive_nextjs_route(file_path)
            component_name = self._extract_nextjs_component_name(content, file_path)
            if not any(p.route_path == route_path for p in result.pages):
                result.pages.append(ScannedPage(
                    component_name=component_name,
                    file_path=rel_path,
                    route_path=route_path,
                ))
            return

        # Next.js App Router: app/**/route.ts → API 路由
        if self._is_nextjs_route_handler(file_path):
            route_path = self._derive_nextjs_route(file_path)
            methods = self._extract_nextjs_route_methods(content)
            for method in methods:
                result.apis.append(ScannedApi(
                    method=method,
                    path=route_path,
                    function_name=method,
                    file_path=rel_path,
                ))
            return

        # Express-style router
        express_route = re.compile(
            r'(?:router|app)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
            re.IGNORECASE,
        )
        for m in express_route.finditer(content):
            result.apis.append(ScannedApi(
                method=m.group(1).upper(),
                path=m.group(2),
                function_name="handler",
                file_path=rel_path,
            ))

        # Vue router definitions
        for m in _VUE_ROUTE.finditer(content):
            route_path = m.group(1)
            component = m.group(2)
            if not any(p.route_path == route_path for p in result.pages):
                result.pages.append(ScannedPage(
                    component_name=component,
                    file_path=rel_path,
                    route_path=route_path,
                ))

    def _is_nextjs_page(self, file_path: Path) -> bool:
        """判断是否为 Next.js App Router 页面文件"""
        return file_path.stem == "page" and file_path.suffix in (".tsx", ".ts", ".jsx", ".js")

    def _is_nextjs_route_handler(self, file_path: Path) -> bool:
        """判断是否为 Next.js Route Handler"""
        return file_path.stem == "route" and file_path.suffix in (".ts", ".tsx", ".js", ".jsx")

    def _derive_nextjs_route(self, file_path: Path) -> str:
        """从 Next.js 文件路径推导路由路径

        例如: app/dashboard/settings/page.tsx → /dashboard/settings
              app/api/users/[id]/route.ts → /api/users/[id]
        """
        parts = file_path.relative_to(self.source_dir).parts

        # 找到 "app" 目录的位置
        app_idx = None
        for i, part in enumerate(parts):
            if part == "app":
                app_idx = i
                break

        if app_idx is None:
            # 没有 app 目录，用相对路径
            route_parts = list(parts[:-1])
        else:
            # 取 app 之后、文件名之前的路径段
            route_parts = list(parts[app_idx + 1:-1])

        # 过滤掉 route group (xxx)
        route_parts = [p for p in route_parts if not (p.startswith("(") and p.endswith(")"))]

        if not route_parts:
            return "/"
        return "/" + "/".join(route_parts)

    def _extract_nextjs_component_name(self, content: str, file_path: Path) -> str:
        """提取 Next.js 页面组件名"""
        # export default function XxxPage
        m = re.search(r'export\s+default\s+function\s+(\w+)', content)
        if m:
            return m.group(1)
        # export default XxxPage
        m = re.search(r'export\s+default\s+(\w+)', content)
        if m:
            return m.group(1)
        # 从目录名推导
        parent = file_path.parent.name
        if parent == "app":
            return "RootPage"
        return parent.replace("-", " ").title().replace(" ", "") + "Page"

    def _extract_nextjs_route_methods(self, content: str) -> List[str]:
        """提取 Next.js Route Handler 导出的 HTTP 方法"""
        methods = []
        for method in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"):
            if re.search(rf'export\s+(?:async\s+)?function\s+{method}\b', content):
                methods.append(method)
        if not methods:
            methods = ["GET"]
        return methods

    def _scan_redis_keys(self, content: str, rel_path: str, result: ScanResult):
        """扫描 Python 文件中的 Redis Key 使用模式"""
        # Strategy 1: Direct string key in redis calls
        # redis.set("key", ...) or redis.get("key")
        redis_direct = re.compile(
            r'(?:redis|self\.redis_client|self\.redis|cache)\.'
            r'(set|get|delete|expire|setex|setnx|hset|hget|hgetall|lpush|rpush|sadd|zadd)'
            r'\s*\(\s*["\']([^"\']+)["\']',
            re.IGNORECASE,
        )
        # Strategy 2: f-string key construction in redis calls
        redis_fstring = re.compile(
            r'(?:redis|self\.redis_client|self\.redis|cache)\.'
            r'(set|get|delete|expire|setex|setnx|hset|hget|hgetall|lpush|rpush|sadd|zadd)'
            r'\s*\(\s*f["\']([^"\']+)["\']',
            re.IGNORECASE,
        )
        # Strategy 3: Key construction patterns (redis_key, KEY_PREFIX, etc.)
        key_construction = re.compile(
            r'(?:redis_key|cache_key|lock_key|key)\s*=\s*(?:'
            r'f["\']([^"\']+)["\']'  # f-string assignment
            r'|["\']([^"\']+)["\']'  # direct string assignment
            r'|.*?redis_key\(\s*f?["\']([^"\']+)["\']'  # settings.redis_key("...")
            r')',
        )
        # Strategy 4: Key prefix constants
        key_prefix = re.compile(
            r'(\w*(?:PREFIX|KEY|PATTERN)\w*)\s*=\s*[f]?["\']([^"\']*[:_][^"\']*)["\']',
        )

        # TTL extraction
        ttl_pattern = re.compile(r'(?:ex|timeout|expire|ttl)\s*=\s*(\d+)')

        seen_keys = set()

        # Run all strategies
        for pattern in [redis_fstring, redis_direct]:
            for m in pattern.finditer(content):
                operation = m.group(1).lower()
                key_pattern = m.group(2)
                key_pattern = re.sub(r'\{[^}]+\}', '{*}', key_pattern)
                self._add_redis_key(key_pattern, operation, content, m, rel_path, result, seen_keys)

        for m in key_construction.finditer(content):
            key_pattern = m.group(1) or m.group(2) or m.group(3)
            if key_pattern and (":" in key_pattern or "_" in key_pattern):
                key_pattern = re.sub(r'\{[^}]+\}', '{*}', key_pattern)
                self._add_redis_key(key_pattern, "cache", content, m, rel_path, result, seen_keys)

        for m in key_prefix.finditer(content):
            prefix_name = m.group(1)
            prefix_value = m.group(2)
            if prefix_value and len(prefix_value) > 2:
                key_pattern = f"{prefix_value}{{*}}"
                self._add_redis_key(key_pattern, "cache", content, m, rel_path, result, seen_keys)

    def _add_redis_key(self, key_pattern: str, operation: str, content: str,
                       match, rel_path: str, result: ScanResult, seen_keys: set):
        """添加 Redis Key 到结果（去重+过滤误报）"""
        if key_pattern in seen_keys or len(key_pattern) < 3:
            return

        # 过滤明显不是 Redis key 的模式
        skip_patterns = (
            "s3://", "http", ".tar.gz", ".json", ".md", ".py",
            "OPENAI_", "WECOM_", "API_KEY", "/v{*}", "temp/", "val[:4]",
        )
        if any(sp in key_pattern for sp in skip_patterns):
            return
        # 过滤路径风格（多个 / 分隔）
        if key_pattern.count("/") >= 2:
            return
        # 过滤纯变量占位（如 {*}{*}、{*}）
        stripped = key_pattern.replace("{*}", "").replace(":", "").replace("_", "").replace("-", "")
        if len(stripped) < 2:
            return

        seen_keys.add(key_pattern)

        # Determine data structure from operation
        data_structure = "String"
        if operation in ("hset", "hget", "hgetall"):
            data_structure = "Hash"
        elif operation in ("lpush", "rpush"):
            data_structure = "List"
        elif operation in ("sadd",):
            data_structure = "Set"
        elif operation in ("zadd",):
            data_structure = "ZSet"

        # Determine semantic type
        op_type = operation
        if "lock" in key_pattern.lower():
            op_type = "lock"
        elif operation in ("set", "setex", "setnx", "hset", "lpush", "rpush", "sadd", "zadd"):
            op_type = "set"
        elif operation in ("get", "hget", "hgetall"):
            op_type = "get"
        elif operation == "delete":
            op_type = "delete"

        # Try to find TTL nearby
        ttl = ""
        ttl_pattern = re.compile(r'(?:ex|timeout|expire|ttl)\s*=\s*(\d+)')
        context_start = max(0, match.start() - 100)
        context_end = min(len(content), match.end() + 300)
        ttl_match = ttl_pattern.search(content[context_start:context_end])
        if ttl_match:
            seconds = int(ttl_match.group(1))
            if seconds < 60:
                ttl = f"{seconds}s"
            elif seconds < 3600:
                ttl = f"{seconds // 60}min"
            else:
                ttl = f"{seconds // 3600}h"

        result.redis_keys.append(ScannedRedisKey(
            key_pattern=key_pattern,
            file_path=rel_path,
            operation=op_type,
            ttl=ttl,
            data_structure=data_structure,
        ))

    def _find_next_function(self, content: str, start: int) -> Optional[str]:
        """找到 start 位置之后的第一个函数定义名"""
        m = re.search(r'(?:async\s+)?def\s+(\w+)', content[start:start + 500])
        if m:
            return m.group(1)
        # JS/TS style
        m = re.search(r'(?:async\s+)?function\s+(\w+)', content[start:start + 500])
        if m:
            return m.group(1)
        return None

    def _extract_docstring(self, content: str, start: int) -> str:
        """提取函数定义后的 docstring"""
        m = re.search(
            r'(?:async\s+)?def\s+\w+\s*\((?:[^()]|\([^()]*\))*\)\s*(?:->\s*[^:]*)?:\s*(?:\n\s+)?["\'"]{3}(.*?)["\'"]{3}',
            content[start:start + 1000],
            re.DOTALL,
        )
        if m:
            return m.group(1).strip().split("\n")[0]
        return ""

    def _extract_orm_columns(self, content: str) -> List[str]:
        """从 SQLAlchemy 模型中提取列名"""
        col_pattern = re.compile(r'(\w+)\s*=\s*(?:Column|mapped_column)\s*\(', re.IGNORECASE)
        columns = []
        for m in col_pattern.finditer(content):
            name = m.group(1)
            if name not in ("__tablename__", "__table_args__", "metadata"):
                columns.append(name)
        return columns
