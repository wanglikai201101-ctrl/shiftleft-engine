"""接口文档生成器"""

from pathlib import Path
from typing import Dict, Any, Optional
from ..models.doc_types import ExtractedApiInfo
from ..models.results import GenerateResult
from ..parsers.registry import ParserRegistry


class ApiDocGenerator:
    """接口文档生成器：从代码提取字段 + 用户补充 → Markdown 文档"""

    def __init__(self, knowledge_base_path: str = "modules"):
        self.kb_path = Path(knowledge_base_path)

    def extract_fields(self, file_path: str, function_name: str) -> Optional[ExtractedApiInfo]:
        """从代码文件提取接口信息"""
        code = Path(file_path).read_text(encoding="utf-8")
        parser = ParserRegistry.get_parser(file_path)
        return parser.extract_api_info(code, function_name)

    def generate(
        self,
        file_path: str,
        function_name: str,
        module: str = "default",
        business_rules: list = None,
        error_cases: list = None,
        related_db: list = None,
        related_page: list = None,
    ) -> GenerateResult:
        """
        生成接口文档

        Args:
            file_path: 代码文件路径
            function_name: 函数名
            module: 模块名
            business_rules: 业务规则列表
            error_cases: 异常场景列表
            related_db: 关联数据库表列表
            related_page: 关联前端页面列表
        """
        try:
            info = self.extract_fields(file_path, function_name)
            if info is None:
                return GenerateResult(success=False, message=f"未找到函数 {function_name}")

            content = self._render_markdown(
                info,
                business_rules=business_rules or [],
                error_cases=error_cases or [],
                related_db=related_db or [],
                related_page=related_page or [],
            )

            identifier = f"{info.method}-{info.path.replace('/', '-').strip('-')}"
            doc_path = self._save(content, module, identifier)

            return GenerateResult(
                success=True,
                message=f"文档已生成：{doc_path}",
                doc_path=doc_path,
                doc_content=content,
                pre_filled_fields={
                    "path": info.path,
                    "method": info.method,
                    "description": info.description,
                    "request_params": [p.name for p in info.request_params],
                },
            )
        except Exception as e:
            return GenerateResult(success=False, message=f"生成文档失败: {e}")

    def _render_markdown(
        self,
        info: ExtractedApiInfo,
        business_rules: list,
        error_cases: list,
        related_db: list,
        related_page: list,
    ) -> str:
        """渲染 Markdown 文档"""
        lines = [f"# {info.method} {info.path}", ""]
        lines += ["## 接口描述", info.description or "待补充", ""]

        # 请求参数
        lines.append("## 请求参数")
        if info.request_params:
            lines.append("| 字段 | 类型 | 必填 | 说明 |")
            lines.append("|------|------|------|------|")
            for p in info.request_params:
                req = "是" if p.required else "否"
                lines.append(f"| {p.name} | {p.type} | {req} | {p.description or '待补充'} |")
        else:
            lines.append("无")
        lines.append("")

        # 业务规则
        lines.append("## 业务规则")
        if business_rules:
            for rule in business_rules:
                lines.append(f"- {rule}")
        else:
            lines.append("待补充")
        lines.append("")

        # 异常场景
        lines.append("## 异常场景")
        if error_cases:
            for err in error_cases:
                lines.append(f"- {err}")
        else:
            lines.append("待补充")
        lines.append("")

        # 关联资源
        lines.append("## 关联资源")
        if related_db:
            lines.append("**数据库表**：")
            for table in related_db:
                lines.append(f"- [storage/db-{table}.md](../storage/db-{table}.md)")
            lines.append("")
        if related_page:
            lines.append("**前端页面**：")
            for page in related_page:
                lines.append(f"- [pages/{page}.md](../pages/{page}.md)")
            lines.append("")

        return "\n".join(lines)

    def _save(self, content: str, module: str, identifier: str) -> str:
        """保存文档到 modules/{module}/apis/"""
        dir_path = self.kb_path / module / "apis"
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / f"{identifier}.md"
        file_path.write_text(content, encoding="utf-8")
        return str(file_path)
