"""批量填充器：多线程并行对所有骨架文档执行 fill。

使用方法：
    from packages.core.batch.batch_fill import BatchFiller
    filler = BatchFiller(modules_dir="modules", source_dir="src/billing")
    result = filler.run(module="billing-agent", workers=8)
"""

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from packages.core.detail_filler.filler import DetailFiller
from packages.core.models.results import FillResult


@dataclass
class BatchFillResult:
    """批量填充结果"""
    total: int = 0
    filled: int = 0
    skipped: int = 0
    failed: int = 0
    details: List[dict] = field(default_factory=list)

    @property
    def summary(self) -> str:
        return f"总计: {self.total} | 已填充: {self.filled} | 跳过: {self.skipped} | 失败: {self.failed}"


class BatchFiller:
    """多线程批量填充文档骨架"""

    def __init__(self, modules_dir: str = "modules", source_dir: str = ""):
        self.modules_dir = Path(modules_dir)
        self.source_dir = Path(source_dir) if source_dir else None
        self.filler = DetailFiller()

    def run(self, module: str, workers: int = 8) -> BatchFillResult:
        """批量填充指定模块的所有文档"""
        result = BatchFillResult()
        module_dir = self.modules_dir / module

        if not module_dir.exists():
            result.details.append({"error": f"模块目录不存在: {module_dir}"})
            return result

        # 收集所有待填充的任务
        tasks = self._collect_tasks(module_dir)
        result.total = len(tasks)

        if not tasks:
            return result

        # 多线程执行
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(self._fill_one, task): task
                for task in tasks
            }
            for future in as_completed(futures):
                task = futures[future]
                try:
                    fill_result = future.result()
                    if fill_result is None:
                        result.skipped += 1
                        result.details.append({
                            "doc": task["doc_path"],
                            "status": "skipped",
                            "reason": "no matching source",
                        })
                    elif fill_result.success:
                        result.filled += 1
                        result.details.append({
                            "doc": task["doc_path"],
                            "status": "filled",
                            "fields": fill_result.filled_fields,
                        })
                    else:
                        result.failed += 1
                        result.details.append({
                            "doc": task["doc_path"],
                            "status": "failed",
                            "reason": fill_result.message,
                        })
                except Exception as e:
                    result.failed += 1
                    result.details.append({
                        "doc": task["doc_path"],
                        "status": "error",
                        "reason": str(e),
                    })

        return result

    def _collect_tasks(self, module_dir: Path) -> List[dict]:
        """收集所有需要填充的文档和对应源文件"""
        tasks = []

        # API 文档
        apis_dir = module_dir / "apis"
        if apis_dir.exists():
            for doc in apis_dir.glob("*.md"):
                source_info = self._find_source_for_doc(doc)
                tasks.append({
                    "doc_path": str(doc),
                    "code_path": source_info.get("code_path"),
                    "function_name": source_info.get("function_name"),
                    "doc_type": "api",
                })

        # Storage 文档
        storage_dir = module_dir / "storage"
        if storage_dir.exists():
            for doc in storage_dir.glob("*.md"):
                source_info = self._find_source_for_doc(doc)
                tasks.append({
                    "doc_path": str(doc),
                    "code_path": source_info.get("code_path"),
                    "function_name": None,
                    "doc_type": "storage",
                })

        # Page 文档
        pages_dir = module_dir / "pages"
        if pages_dir.exists():
            for doc in pages_dir.glob("*.md"):
                source_info = self._find_source_for_doc(doc)
                tasks.append({
                    "doc_path": str(doc),
                    "code_path": source_info.get("code_path"),
                    "function_name": None,
                    "doc_type": "page",
                })

        return tasks

    def _find_source_for_doc(self, doc_path: Path) -> dict:
        """从文档骨架中提取源文件引用"""
        try:
            content = doc_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return {}

        # 尝试从 "> 源函数: `file::function`" 格式提取
        m = re.search(r'源函数: `([^`]+)`', content)
        if m:
            ref = m.group(1)
            parts = ref.split("::")
            code_path = parts[0]
            func_name = parts[1] if len(parts) > 1 else None
            # 转为绝对路径
            if self.source_dir:
                full_path = self.source_dir / code_path
                if full_path.exists():
                    return {"code_path": str(full_path), "function_name": func_name}
            return {"code_path": code_path, "function_name": func_name}

        # 尝试从 "> 来源: `file` (type)" 格式提取
        m = re.search(r'来源: `([^`]+)`', content)
        if m:
            ref = m.group(1).split(" ")[0]
            if self.source_dir:
                full_path = self.source_dir / ref
                if full_path.exists():
                    return {"code_path": str(full_path)}
                # Fallback: search recursively for the filename
                found = self._find_file_recursive(ref)
                if found:
                    return {"code_path": str(found)}
            return {"code_path": ref}

        # 尝试从 "> 组件: `file`" 格式提取（前端页面文档）
        m = re.search(r'组件: `([^`]+)`', content)
        if m:
            ref = m.group(1)
            if self.source_dir:
                full_path = self.source_dir / ref
                if full_path.exists():
                    return {"code_path": str(full_path)}
                # Fallback: search recursively for the filename
                found = self._find_file_recursive(ref)
                if found:
                    return {"code_path": str(found)}
            return {"code_path": ref}

        return {}

    def _find_file_recursive(self, ref: str) -> Optional[Path]:
        """在 source_dir 下递归查找匹配的文件"""
        if not self.source_dir:
            return None
        filename = Path(ref).name
        skip_dirs = {"node_modules", ".venv", "__pycache__", ".git", "dist", "build", ".next"}
        for path in self.source_dir.rglob(filename):
            if not any(p in path.parts for p in skip_dirs):
                # Prefer paths that end with the full ref
                if str(path).replace("\\", "/").endswith(ref.replace("\\", "/")):
                    return path
        # If no exact suffix match, return first found
        for path in self.source_dir.rglob(filename):
            if not any(p in path.parts for p in skip_dirs):
                return path
        return None

    def _fill_one(self, task: dict) -> Optional[FillResult]:
        """填充单个文档"""
        code_path = task.get("code_path")
        if not code_path or not Path(code_path).exists():
            return None

        return self.filler.fill(
            skeleton_path=task["doc_path"],
            code_path=code_path,
            function_name=task.get("function_name"),
        )
