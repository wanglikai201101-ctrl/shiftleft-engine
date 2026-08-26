"""Python 代码解析器：基于 AST 提取接口信息"""

import ast
from typing import Optional
from .base import BaseParser
from ..models.doc_types import ExtractedApiInfo, ApiField


class PythonApiParser(BaseParser):
    """Python 接口代码解析器（FastAPI / Flask 风格）"""

    def extract_api_info(self, code: str, function_name: str) -> Optional[ExtractedApiInfo]:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return None

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
                method, path = self._extract_decorator(node)
                description = ast.get_docstring(node) or ""
                request_params = self._extract_function_params(node)
                response_model = self._extract_response_model(node)
                response_fields = self._extract_model_fields(tree, response_model) if response_model else []

                return ExtractedApiInfo(
                    path=path,
                    method=method,
                    description=description,
                    function_name=function_name,
                    request_params=request_params,
                    response_fields=response_fields,
                )

        return None

    def _extract_response_model(self, node: ast.FunctionDef) -> str:
        """提取装饰器中 response_model 引用的模型名"""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                for kw in decorator.keywords:
                    if kw.arg == "response_model":
                        value = kw.value
                        if isinstance(value, ast.Name):
                            return value.id
                        if isinstance(value, ast.Attribute):
                            return value.attr
        return ""

    def _extract_model_fields(self, tree, model_name: str) -> list:
        """从同文件中的模型类提取响应字段（Pydantic 风格）"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == model_name:
                fields = []
                for stmt in node.body:
                    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                        fields.append(ApiField(
                            name=stmt.target.id,
                            type=self._annotation_to_type(stmt.annotation),
                        ))
                return fields
        return []

    def _extract_decorator(self, node: ast.FunctionDef) -> tuple:
        """提取装饰器中的 HTTP 方法和路径"""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                method = decorator.func.attr.upper()
                if decorator.args and isinstance(decorator.args[0], ast.Constant):
                    return method, decorator.args[0].value
        return "UNKNOWN", "/unknown"

    def _extract_function_params(self, node: ast.FunctionDef) -> list:
        """提取函数参数"""
        params = []
        for arg in node.args.args:
            if arg.arg in ("self", "request", "db", "session"):
                continue
            param_type = "string"
            if arg.annotation and isinstance(arg.annotation, ast.Name):
                param_type = arg.annotation.id.lower()
            params.append(ApiField(name=arg.arg, type=param_type))
        return params

    @staticmethod
    def _annotation_to_type(annotation) -> str:
        """把 AST 注解节点转为字符串类型名，失败回退 string"""
        try:
            s = ast.unparse(annotation)
            return s.strip() or "string"
        except Exception:
            return "string"
