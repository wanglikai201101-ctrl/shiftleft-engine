"""
MCP Server 入口

每个 Tool 是 core 层的薄壳封装：接收参数 → 调用 core → 返回 JSON。
依赖 mcp SDK: pip install mcp

启动方式：
  stdio 模式: python -m packages.mcp_server.server
  HTTP 模式: 需额外配置 uvicorn（二期）
"""

import json
import os
import re
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict

# MCP SDK 延迟导入，允许在未安装 mcp 时仍可使用 core 层
try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    HAS_MCP = True
except ImportError:
    HAS_MCP = False

from packages.core.generators.api_doc import ApiDocGenerator
from packages.core.validators.linter import DocLinter
from packages.core.requirement_decomposer.decomposer import RequirementDecomposer
from packages.core.detail_filler.filler import DetailFiller
from packages.core.indexing.traceability import TraceabilityQuery
from packages.core.indexing.indexer import DocumentIndexer

_SAFE_PATH_PATTERN = re.compile(r"^[a-zA-Z0-9_\-./\\]+$")


def _validate_path(path: str, label: str = "path") -> str:
    """校验路径参数，防止路径遍历和命令注入。"""
    if not path:
        raise ValueError(f"{label} 不能为空")
    if not _SAFE_PATH_PATTERN.match(path):
        raise ValueError(f"非法 {label}: {path!r}，包含不允许的字符")
    normalized = os.path.normpath(path)
    if normalized.startswith("..") or "/../" in path or path.startswith("/"):
        raise ValueError(f"路径遍历检测: {path!r}")
    return path


def _json_response(data: Any) -> str:
    """统一 JSON 序列化"""
    if is_dataclass(data) and not isinstance(data, type):
        return json.dumps(asdict(data), ensure_ascii=False, default=str)
    if hasattr(data, "__dict__"):
        d = {}
        for k, v in data.__dict__.items():
            if is_dataclass(v) and not isinstance(v, type):
                d[k] = asdict(v)
            elif isinstance(v, list):
                d[k] = [
                    asdict(item) if (is_dataclass(item) and not isinstance(item, type)) else
                    (item.__dict__ if hasattr(item, "__dict__") else item)
                    for item in v
                ]
            else:
                d[k] = v
        return json.dumps(d, ensure_ascii=False, default=str)
    return json.dumps(data, ensure_ascii=False, default=str)


def _lint_report_to_dict(report) -> dict:
    """Convert a LintReport to a serializable dict."""
    return {
        "passed": report.passed,
        "errors": report.error_count,
        "warnings": report.warning_count,
        "issues": {k: [str(i) for i in v] for k, v in report.issues.items()},
    }


def create_server() -> "Server":
    """创建并配置 MCP Server"""
    if not HAS_MCP:
        raise RuntimeError("需要安装 mcp SDK: pip install mcp")

    app = Server("knowledge-base")

    @app.list_tools()
    async def list_tools() -> list:
        return [
            # --- New requirement-driven tools ---
            Tool(
                name="decompose_requirement",
                description="从需求文档分解关联关系并生成文档骨架",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "requirement_doc_path": {
                            "type": "string",
                            "description": "需求文档路径（如 modules/user-auth/requirements/REQ-UA-001.md）",
                        },
                    },
                    "required": ["requirement_doc_path"],
                },
            ),
            Tool(
                name="fill_technical_details",
                description="从代码提取技术细节填入文档骨架",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "skeleton_path": {
                            "type": "string",
                            "description": "文档骨架文件路径",
                        },
                        "code_path": {
                            "type": "string",
                            "description": "代码文件路径",
                        },
                        "function_name": {
                            "type": "string",
                            "description": "函数名（可选，不指定时尝试从骨架推断）",
                        },
                    },
                    "required": ["skeleton_path", "code_path"],
                },
            ),
            Tool(
                name="check_code_conformance",
                description="检查代码是否匹配文档（代码符合性检查）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "module": {
                            "type": "string",
                            "description": "模块名（检查整个模块）",
                        },
                        "doc_path": {
                            "type": "string",
                            "description": "单个文档路径（检查单个文档）",
                        },
                    },
                },
            ),
            Tool(
                name="query_traceability",
                description="从任意标识符查询完整追溯链（文档路径/REQ-xxx/TP-xxx）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "identifier": {
                            "type": "string",
                            "description": "查询标识符（文档路径、REQ-xxx 或 TP-xxx）",
                        },
                    },
                    "required": ["identifier"],
                },
            ),
            Tool(
                name="generate_index",
                description="生成文档索引（docs-index.json）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "output_path": {
                            "type": "string",
                            "description": "输出路径（默认 docs-index.json）",
                        },
                    },
                },
            ),
            # --- Legacy tools (preserved) ---
            Tool(
                name="generate_api_doc",
                description="从 Python 代码生成 API 接口文档",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "code_path": {"type": "string", "description": "代码文件路径"},
                        "function_name": {"type": "string", "description": "函数名"},
                        "module": {"type": "string", "description": "模块名"},
                        "business_rules": {"type": "array", "items": {"type": "string"}},
                        "error_cases": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["code_path", "function_name", "module"],
                },
            ),
            Tool(
                name="lint_module",
                description="检查指定模块的文档一致性",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "module_name": {"type": "string", "description": "模块名"},
                    },
                    "required": ["module_name"],
                },
            ),
            Tool(
                name="lint_all",
                description="检查所有文档的一致性",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list:
        # --- New requirement-driven tools ---
        if name == "decompose_requirement":
            try:
                req_path = _validate_path(arguments["requirement_doc_path"], "requirement_doc_path")
                decomposer = RequirementDecomposer()
                result = decomposer.decompose(req_path)
                return [TextContent(type="text", text=_json_response(result))]
            except Exception as e:
                return [TextContent(type="text", text=json.dumps(
                    {"error": str(e)}, ensure_ascii=False
                ))]

        elif name == "fill_technical_details":
            try:
                skeleton_path = _validate_path(arguments["skeleton_path"], "skeleton_path")
                code_path = _validate_path(arguments["code_path"], "code_path")
                filler = DetailFiller()
                result = filler.fill(
                    skeleton_path=skeleton_path,
                    code_path=code_path,
                    function_name=arguments.get("function_name"),
                )
                return [TextContent(type="text", text=_json_response(result))]
            except Exception as e:
                return [TextContent(type="text", text=json.dumps(
                    {"error": str(e)}, ensure_ascii=False
                ))]

        elif name == "check_code_conformance":
            try:
                doc_path = arguments.get("doc_path")
                module = arguments.get("module")
                if doc_path:
                    _validate_path(doc_path, "doc_path")
                if module:
                    _validate_path(module, "module")
                linter = DocLinter()
                report = linter.check_code_conformance(
                    doc_path=doc_path,
                    module=module,
                )
                return [TextContent(type="text", text=_json_response(
                    _lint_report_to_dict(report)
                ))]
            except Exception as e:
                return [TextContent(type="text", text=json.dumps(
                    {"error": str(e)}, ensure_ascii=False
                ))]

        elif name == "generate_index":
            try:
                output_path = arguments.get("output_path", "docs-index.json")
                _validate_path(output_path, "output_path")
                indexer = DocumentIndexer()
                index = indexer.generate_index(output_path=output_path)
                return [TextContent(type="text", text=_json_response(index))]
            except Exception as e:
                return [TextContent(type="text", text=json.dumps(
                    {"error": str(e)}, ensure_ascii=False
                ))]

        # --- Legacy tools (preserved) ---
        elif name == "generate_api_doc":
            _validate_path(arguments["code_path"], "code_path")
            gen = ApiDocGenerator()
            result = gen.generate(
                file_path=arguments["code_path"],
                function_name=arguments["function_name"],
                module=arguments.get("module", "default"),
                business_rules=arguments.get("business_rules"),
                error_cases=arguments.get("error_cases"),
            )
            return [TextContent(type="text", text=_json_response(result))]

        elif name == "lint_module":
            linter = DocLinter()
            report = linter.check_module(arguments["module_name"])
            return [TextContent(type="text", text=_json_response(
                _lint_report_to_dict(report)
            ))]

        elif name == "lint_all":
            linter = DocLinter()
            report = linter.check_all()
            return [TextContent(type="text", text=_json_response(
                _lint_report_to_dict(report)
            ))]

        return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

    return app


if __name__ == "__main__":
    app = create_server()
    app.run()
