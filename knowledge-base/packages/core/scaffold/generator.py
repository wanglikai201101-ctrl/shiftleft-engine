"""骨架生成器：将扫描结果转化为模块文档目录结构。

使用方法：
    from packages.core.scaffold import CodeScanner, ScaffoldGenerator

    scanner = CodeScanner("src/billing/")
    scan_result = scanner.scan()

    generator = ScaffoldGenerator(output_dir="modules", module_name="billing")
    gen_result = generator.generate(scan_result)
    # gen_result.generated_files = ["modules/billing/MODULE.md", ...]
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from .scanner import ScanResult, ScannedApi, ScannedTable, ScannedPage, ScannedJob, ScannedRedisKey


@dataclass
class ScaffoldResult:
    """骨架生成结果"""
    success: bool
    module_name: str
    output_dir: str
    generated_files: List[str] = field(default_factory=list)
    skipped_files: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    message: str = ""

    @property
    def summary(self) -> str:
        return (
            f"模块: {self.module_name} | "
            f"生成: {len(self.generated_files)} | "
            f"跳过: {len(self.skipped_files)} | "
            f"错误: {len(self.errors)}"
        )


class ScaffoldGenerator:
    """将 ScanResult 转化为模块文档目录结构"""

    def __init__(self, output_dir: str = "modules", module_name: str = ""):
        self.output_dir = Path(output_dir)
        self.module_name = module_name

    def generate(self, scan_result: ScanResult) -> ScaffoldResult:
        """从扫描结果生成完整模块文档骨架"""
        result = ScaffoldResult(
            success=True,
            module_name=self.module_name,
            output_dir=str(self.output_dir),
        )

        module_dir = self.output_dir / self.module_name
        module_dir.mkdir(parents=True, exist_ok=True)

        # 生成 MODULE.md
        self._generate_module_md(module_dir, scan_result, result)

        # 生成 apis/
        for api in scan_result.apis:
            self._generate_api_skeleton(module_dir, api, result)

        # 生成 storage/
        for table in scan_result.tables:
            self._generate_storage_skeleton(module_dir, table, result)

        # 生成 pages/
        for page in scan_result.pages:
            self._generate_page_skeleton(module_dir, page, result)

        # 生成 jobs/
        for job in scan_result.jobs:
            self._generate_job_skeleton(module_dir, job, result)

        # 生成 storage/redis-*.md
        for redis_key in scan_result.redis_keys:
            self._generate_redis_skeleton(module_dir, redis_key, result)

        result.message = f"骨架生成完成: {result.summary}"
        return result

    def _write_if_not_exists(self, path: Path, content: str, result: ScaffoldResult):
        """写入文件，已存在则跳过"""
        if path.exists():
            result.skipped_files.append(str(path))
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            result.generated_files.append(str(path))
        except Exception as e:
            result.errors.append(f"{path}: {e}")

    def _generate_module_md(self, module_dir: Path, scan: ScanResult, result: ScaffoldResult):
        """生成 MODULE.md 总纲"""
        lines = [
            f"# {self.module_name} 模块",
            "",
            "> 版本：v1.0 | 创建时间：待补充 | 负责人：待补充",
            "",
            "## 业务概述",
            "",
            "待补充",
            "",
            "## 需求追溯",
            "",
            "| 需求编号 | 需求名称 | 涉及接口 | 涉及表 | 涉及页面 |",
            "|---------|---------|---------|--------|---------|",
            "| 待补充 | 待补充 | 待补充 | 待补充 | 待补充 |",
            "",
            "## 模块资产清单",
            "",
            "| 类型 | 数量 | 目录 |",
            "|------|------|------|",
            f"| 接口文档 | {len({(a.method, a.path) for a in scan.apis})} | apis/ |",
            f"| 存储文档 | {len({t.table_name for t in scan.tables})} | storage/ |",
            f"| 前端页面文档 | {len({p.component_name for p in scan.pages})} | pages/ |",
            f"| 定时任务文档 | {len({j.job_name for j in scan.jobs})} | jobs/ |",
            "",
            "## 扫描来源",
            "",
            "| 类型 | 标识 | 源文件 |",
            "|------|------|--------|",
        ]

        seen_apis: set = set()
        for api in scan.apis:
            key = (api.method, api.path)
            if key in seen_apis:
                continue
            seen_apis.add(key)
            lines.append(f"| API | {api.method} {api.path} | {api.file_path} |")
        seen_tables: set = set()
        for table in scan.tables:
            if table.table_name in seen_tables:
                continue
            seen_tables.add(table.table_name)
            lines.append(f"| 表 | {table.table_name} | {table.file_path} |")
        seen_pages: set = set()
        for page in scan.pages:
            if page.component_name in seen_pages:
                continue
            seen_pages.add(page.component_name)
            lines.append(f"| 页面 | {page.component_name} | {page.file_path} |")
        seen_jobs: set = set()
        for job in scan.jobs:
            if job.job_name in seen_jobs:
                continue
            seen_jobs.add(job.job_name)
            lines.append(f"| 任务 | {job.job_name} | {job.file_path} |")

        lines.append("")
        self._write_if_not_exists(module_dir / "MODULE.md", "\n".join(lines), result)

    def _generate_api_skeleton(self, module_dir: Path, api: ScannedApi, result: ScaffoldResult):
        """生成单个接口文档骨架"""
        safe_name = f"{api.method}-{api.path.strip('/').replace('/', '-')}"
        file_path = module_dir / "apis" / f"{safe_name}.md"

        description = api.description or "待补充"
        lines = [
            f"# {api.method} {api.path} — {description}",
            "",
            f"> 源函数: `{api.file_path}::{api.function_name}`",
            "",
            "## 基本信息",
            "",
            "| 字段 | 值 |",
            "|------|-----|",
            f"| 模块 | {self.module_name} |",
            f"| 方法 | {api.method} |",
            f"| 路径 | {api.path} |",
            "| 认证 | 待补充 |",
            f"| 代码位置 | `{api.function_name}` — 待补充 |",
            "| 负责人 | 待补充 |",
            "| 需求来源 | 待补充 |",
            "| 版本 | v1.0 |",
            "",
            "## 请求参数",
            "",
            "| 参数 | 类型 | 必填 | 来源 | 说明 |",
            "|------|------|------|------|------|",
            "| 待补充 | 待补充 | 待补充 | 待补充 | 待补充 |",
            "",
            "> \"来源\"列必填：标明参数值从哪个接口/页面获取",
            "",
            "## 响应结构",
            "",
            "| 字段 | 类型 | 流向 | 说明 |",
            "|------|------|------|------|",
            "| 待补充 | 待补充 | 待补充 | 待补充 |",
            "",
            "> \"流向\"列必填：标明返回字段被哪个接口/页面消费",
            "",
            "## 依赖接口（上游）",
            "",
            "| 接口 | 传递的字段 | 关系 |",
            "|------|----------|------|",
            "| 待补充 | 待补充 | 待补充 |",
            "",
            "## 被依赖接口（下游）",
            "",
            "| 接口 | 消费的字段 | 关系 |",
            "|------|----------|------|",
            "| 待补充 | 待补充 | 待补充 |",
            "",
            "## 关联数据库",
            "",
            "| 表 | 操作 | 字段 | 业务规则 | 说明 |",
            "|-----|------|------|---------|------|",
            "| 待补充 | 待补充 | 待补充 | 待补充 | 待补充 |",
            "",
            "> \"业务规则\"列必填：写明具体的计算/判断逻辑",
            "",
            "## 关联定时任务",
            "",
            "| 任务 | 关系 | 触发条件 |",
            "|------|------|---------|",
            "| 待补充 | 待补充 | 待补充 |",
            "",
            "## 关联前端页面",
            "",
            "| 页面 | 触发元素(data-testid) | 触发方式 |",
            "|------|----------------------|--------|",
            "| 待补充 | 待补充 | 待补充 |",
            "",
            "## 错误码",
            "",
            "| 错误码 | 说明 | 前端处理 |",
            "|--------|------|--------|",
            "| 待补充 | 待补充 | 待补充 |",
            "",
            "## 变更记录",
            "",
            "| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 关联需求/缺陷 |",
            "|------|------|--------|--------|--------|-------------|",
            "| v1.0 | 待补充 | scaffold 自动生成 | 无（新建） | 从代码反推骨架 | 待补充 |",
            "",
        ]

        self._write_if_not_exists(file_path, "\n".join(lines), result)

    def _generate_storage_skeleton(self, module_dir: Path, table: ScannedTable, result: ScaffoldResult):
        """生成单个存储文档骨架"""
        file_path = module_dir / "storage" / f"{table.table_name}.md"

        lines = [
            f"# {table.table_name} — 待补充",
            "",
            f"> 来源: `{table.file_path}` ({table.source_type})",
            "",
            "## 基本信息",
            "",
            "| 字段 | 值 |",
            "|------|-----|",
            f"| 存储类型 | 关系型数据库 (PostgreSQL) |",
            f"| 模块 | {self.module_name} |",
            f"| 表名 | {table.table_name} |",
            "| 负责人 | 待补充 |",
            "| 需求来源 | 待补充 |",
            "| 版本 | v1.0 |",
            "",
            "## 字段定义",
            "",
            "| 字段 | 类型 | 索引 | 写入来源 | 读取去向 | 业务规则 | 说明 |",
            "|------|------|------|---------|---------|---------|------|",
        ]

        if table.columns:
            for col in table.columns:
                lines.append(f"| {col} | 待补充 | 待补充 | 待补充 | 待补充 | 待补充 | 待补充 |")
        else:
            lines.append("| 待补充 | 待补充 | 待补充 | 待补充 | 待补充 | 待补充 | 待补充 |")

        lines.extend([
            "",
            "> \"写入来源\"：哪个接口/任务写入此字段。\"读取去向\"：哪个接口/页面读取此字段。\"业务规则\"：计算逻辑或约束条件。",
            "",
            "## 索引设计",
            "",
            "| 索引名 | 类型 | 字段 | 说明 |",
            "|--------|------|------|------|",
            "| 待补充 | 待补充 | 待补充 | 待补充 |",
            "",
            "## 状态流转（如有状态字段）",
            "",
            "待补充",
            "",
            "## 并发控制",
            "",
            "| 场景 | 控制方式 | 实现 | 说明 |",
            "|------|---------|------|------|",
            "| 待补充 | 待补充 | 待补充 | 待补充 |",
            "",
            "## 关联接口",
            "",
            "| 接口 | 操作 | 涉及字段 |",
            "|------|------|--------|",
            "| 待补充 | 待补充 | 待补充 |",
            "",
            "## 关联定时任务",
            "",
            "| 任务 | 操作 | 条件 |",
            "|------|------|------|",
            "| 待补充 | 待补充 | 待补充 |",
            "",
            "## 关联表",
            "",
            "| 表 | 关系 | 关联字段 | 数据流向 |",
            "|-----|------|---------|--------|",
            "| 待补充 | 待补充 | 待补充 | 待补充 |",
            "",
            "## 关联其他存储",
            "",
            "| 存储节点 | 类型 | 关系 | 说明 |",
            "|---------|------|------|------|",
            "| 待补充 | 待补充 | 待补充 | 待补充 |",
            "",
            "## 变更记录",
            "",
            "| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 关联需求/缺陷 |",
            "|------|------|--------|--------|--------|-------------|",
            "| v1.0 | 待补充 | scaffold 自动生成 | 无（新建） | 从代码反推骨架 | 待补充 |",
            "",
        ])

        self._write_if_not_exists(file_path, "\n".join(lines), result)

    def _generate_page_skeleton(self, module_dir: Path, page: ScannedPage, result: ScaffoldResult):
        """生成单个页面文档骨架"""
        safe_name = page.component_name or page.route_path.strip("/").replace("/", "-") or "unknown"
        file_path = module_dir / "pages" / f"{safe_name}.md"

        lines = [
            f"# {safe_name} — 待补充",
            "",
            f"> 组件: `{page.file_path}`",
        ]

        if page.route_path:
            lines.append(f"> 路由: `{page.route_path}`")

        lines.extend([
            "",
            "## 基本信息",
            "",
            "| 字段 | 值 |",
            "|------|-----|",
            f"| 模块 | {self.module_name} |",
            f"| 路由 | {page.route_path or '待补充'} |",
            f"| 组件 | {page.file_path} |",
            "| 负责人 | 待补充 |",
            "| 需求来源 | 待补充 |",
            "| 版本 | v1.0 |",
            "",
            "## 页面元素清单",
            "",
            "| data-testid | 元素类型 | 功能 | 触发接口 | 绑定字段 | 数据来源 |",
            "|-------------|---------|------|---------|---------|--------|",
        ])

        if page.testids:
            for testid in page.testids:
                lines.append(f"| {testid} | 待补充 | 待补充 | 待补充 | 待补充 | 待补充 |")
        else:
            lines.append("| 待补充 | 待补充 | 待补充 | 待补充 | 待补充 | 待补充 |")

        lines.extend([
            "",
            "> \"绑定字段\"：展示类用 `← field`（来自接口），输入类用 `→ param`（提交给接口）",
            "",
            "## 接口调用顺序",
            "",
            "页面加载：",
            "1. 待补充",
            "",
            "用户操作：",
            "1. 待补充",
            "",
            "## 数据流转",
            "",
            "| 数据 | 来源 | 展示元素 | 流向 |",
            "|------|------|---------|------|",
            "| 待补充 | 待补充 | 待补充 | 待补充 |",
            "",
            "## 变更记录",
            "",
            "| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 关联需求/缺陷 |",
            "|------|------|--------|--------|--------|-------------|",
            "| v1.0 | 待补充 | scaffold 自动生成 | 无（新建） | 从代码反推骨架 | 待补充 |",
            "",
        ])

        self._write_if_not_exists(file_path, "\n".join(lines), result)

    def _generate_job_skeleton(self, module_dir: Path, job: ScannedJob, result: ScaffoldResult):
        """生成单个定时任务文档骨架"""
        file_path = module_dir / "jobs" / f"{job.job_name}.md"

        description = job.description or "待补充"
        lines = [
            f"# {job.job_name} — {description}",
            "",
            f"> 源文件: `{job.file_path}`",
        ]

        if job.schedule:
            lines.append(f"> 调度: `{job.schedule}`")

        lines.extend([
            "",
            "## 基本信息",
            "",
            "| 字段 | 值 |",
            "|------|-----|",
            f"| 模块 | {self.module_name} |",
            f"| 任务名 | {job.job_name} |",
            f"| 调度策略 | {job.schedule or '待补充'} |",
            "| 需求来源 | 待补充 |",
            "",
            "## 触发与取消条件",
            "",
            "| 条件 | 来源 | 说明 |",
            "|------|------|------|",
            "| 待补充 | 待补充 | 待补充 |",
            "",
            "## 关联数据库",
            "",
            "| 表 | 操作 | 字段 | 业务规则 | 说明 |",
            "|-----|------|------|---------|------|",
            "| 待补充 | 待补充 | 待补充 | 待补充 | 待补充 |",
            "",
            "## 关联接口",
            "",
            "| 接口 | 关系 | 说明 |",
            "|------|------|------|",
            "| 待补充 | 待补充 | 待补充 |",
            "",
            "## 监控",
            "",
            "| 指标 | 阈值 | 告警方式 |",
            "|------|------|--------|",
            "| 待补充 | 待补充 | 待补充 |",
            "",
            "## 变更记录",
            "",
            "| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 影响范围 |",
            "|------|------|--------|--------|--------|--------|",
            "| v1.0 | 待补充 | scaffold 自动生成 | 无（新建） | 从代码反推骨架 | 待补充 |",
            "",
        ])

        self._write_if_not_exists(file_path, "\n".join(lines), result)

    def _generate_redis_skeleton(self, module_dir: Path, redis_key: ScannedRedisKey, result: ScaffoldResult):
        """生成单个 Redis Key 文档骨架"""
        safe_name = redis_key.key_pattern.replace(":", "-").replace("{*}", "x").replace("/", "-")
        file_path = module_dir / "storage" / f"redis-{safe_name}.md"

        lines = [
            f"# redis-{safe_name} — 待补充",
            "",
            f"> 来源: `{redis_key.file_path}`",
            "",
            "## 基本信息",
            "",
            "| 字段 | 值 |",
            "|------|-----|",
            "| 存储类型 | Redis |",
            f"| 模块 | {self.module_name} |",
            f"| Key 模式 | `{redis_key.key_pattern}` |",
            f"| 数据结构 | {redis_key.data_structure} |",
            f"| TTL | {redis_key.ttl or '待补充'} |",
            "| 负责人 | 待补充 |",
            "| 需求来源 | 待补充 |",
            "| 版本 | v1.0 |",
            "",
            "## 写入场景",
            "",
            "| 触发接口/任务 | 操作 | Key 示例 | 业务规则 |",
            "|-------------|------|---------|---------|",
            "| 待补充 | 待补充 | 待补充 | 待补充 |",
            "",
            "## 读取场景",
            "",
            "| 消费接口/任务 | 操作 | 缓存未命中时 | 说明 |",
            "|-------------|------|------------|------|",
            "| 待补充 | 待补充 | 待补充 | 待补充 |",
            "",
            "## 过期策略",
            "",
            "| Key 模式 | TTL | 刷新策略 | 说明 |",
            "|---------|-----|---------|------|",
            f"| `{redis_key.key_pattern}` | {redis_key.ttl or '待补充'} | 待补充 | 待补充 |",
            "",
            "## 关联接口",
            "",
            "| 接口 | 操作 | Key 模式 | 说明 |",
            "|------|------|---------|------|",
            "| 待补充 | 待补充 | 待补充 | 待补充 |",
            "",
            "## 关联数据库",
            "",
            "| 表 | 关系 | 说明 |",
            "|-----|------|------|",
            "| 待补充 | 待补充 | 待补充 |",
            "",
            "## 变更记录",
            "",
            "| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 关联需求/缺陷 |",
            "|------|------|--------|--------|--------|-------------|",
            "| v1.0 | 待补充 | scaffold 自动生成 | 无（新建） | 从代码反推骨架 | 待补充 |",
            "",
        ]

        self._write_if_not_exists(file_path, "\n".join(lines), result)