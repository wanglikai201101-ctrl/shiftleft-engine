"""
文档填写助手（DocGuardian）

研发在写完代码后，主动调用此工具快速生成知识库文档。
工具会自动从代码中提取字段（预填充 80%），研发只需补充业务逻辑（20%）。

使用方式：
1. 命令行：python -m tools.knowledge_base.doc_guardian api --file sevice/api/order.py --function create_order
2. AI 调用：通过 MCP 工具调用（研发说"帮我生成接口文档"）

作者：示例团队
创建时间：2025-04-20
"""

import ast
import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import argparse


class FieldExtractor:
    """从代码中提取文档字段，减少研发手动填写"""

    def extract_api_fields(self, code: str, function_name: str) -> Dict[str, Any]:
        """
        从接口代码中提取字段

        Args:
            code: Python 代码字符串
            function_name: 函数名（如 create_order）

        Returns:
            {
                "path": "/orders",
                "method": "POST",
                "description": "创建订单",
                "request_params": {
                    "order_no": {"type": "string", "required": True, "description": "订单号"},
                    "amount": {"type": "number", "required": True, "description": "订单金额"}
                },
                "response_fields": {...}
            }
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {"error": f"代码解析失败: {e}"}

        for node in ast.walk(tree):
            # 支持同步和异步函数
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
                # 提取装饰器（@app.post("/orders")）
                method, path = self._extract_decorator(node)

                # 提取 docstring
                description = ast.get_docstring(node) or ""

                # 提取请求参数（从函数参数的类型注解）
                request_params = self._extract_function_params(node)

                return {
                    "path": path,
                    "method": method,
                    "description": description,
                    "request_params": request_params,
                    "function_name": function_name
                }

        return {"error": f"未找到函数 {function_name}"}

    def _extract_decorator(self, node: ast.FunctionDef) -> tuple:
        """提取装饰器中的 HTTP 方法和路径"""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                # 提取方法名（如 app.post → POST）
                if isinstance(decorator.func, ast.Attribute):
                    method = decorator.func.attr.upper()

                    # 提取路径（第一个参数）
                    if decorator.args and isinstance(decorator.args[0], ast.Constant):
                        path = decorator.args[0].value
                        return method, path

        return "UNKNOWN", "/unknown"

    def _extract_function_params(self, node: ast.FunctionDef) -> Dict[str, Dict]:
        """提取函数参数（简化版，实际需要解析 Pydantic 模型）"""
        params = {}

        for arg in node.args.args:
            if arg.arg == "self" or arg.arg == "request":
                continue

            param_name = arg.arg
            param_type = "string"  # 默认类型

            # 尝试从类型注解提取类型
            if arg.annotation:
                if isinstance(arg.annotation, ast.Name):
                    param_type = arg.annotation.id.lower()

            params[param_name] = {
                "type": param_type,
                "required": True,
                "description": ""
            }

        return params


class DocTemplateGenerator:
    """生成文档并保存到 knowledge-base"""

    def __init__(self, knowledge_base_path: str = "knowledge-base"):
        self.kb_path = Path(knowledge_base_path)

    def generate_api_doc(self, fields: Dict[str, Any], user_input: Dict[str, Any]) -> str:
        """
        生成接口文档

        Args:
            fields: 从代码中提取的字段（预填充）
            user_input: 研发补充的信息
                {
                    "module": "order",
                    "business_rules": ["订单金额必须 >0", "订单明细不能为空"],
                    "error_cases": ["库存不足返回 400", "用户余额不足返回 402"],
                    "related_db": ["t_order", "t_order_item"],
                    "related_page": ["OrderCreate.vue"]
                }

        Returns:
            Markdown 文档内容
        """
        template = f"""# {fields['method']} {fields['path']}

## 接口描述
{fields.get('description', '待补充')}

## 请求参数
"""

        # 填充请求参数表格
        if fields.get('request_params'):
            template += "| 字段 | 类型 | 必填 | 说明 |\n"
            template += "|------|------|------|------|\n"
            for param, info in fields['request_params'].items():
                required = "是" if info.get('required', True) else "否"
                desc = info.get('description', '待补充')
                template += f"| {param} | {info['type']} | {required} | {desc} |\n"
        else:
            template += "无\n"

        # 添加研发补充的业务规则
        template += "\n## 业务规则\n"
        if user_input.get('business_rules'):
            for rule in user_input['business_rules']:
                template += f"- {rule}\n"
        else:
            template += "待补充\n"

        # 添加异常场景
        template += "\n## 异常场景\n"
        if user_input.get('error_cases'):
            for error in user_input['error_cases']:
                template += f"- {error}\n"
        else:
            template += "待补充\n"

        # 添加关联资源
        template += "\n## 关联资源\n"
        if user_input.get('related_db'):
            template += "**数据库表**：\n"
            for table in user_input['related_db']:
                template += f"- [[file:../database/{table}.md]]\n"

        if user_input.get('related_page'):
            template += "\n**前端页面**：\n"
            for page in user_input['related_page']:
                template += f"- [[file:../page/{page}.md]]\n"

        return template


    def save_doc(self, doc_type: str, content: str, module: str, identifier: str) -> str:
        """
        保存文档到 knowledge-base

        Args:
            doc_type: 文档类型（api/database/page/job/config）
            content: 文档内容
            module: 模块名（如 order）
            identifier: 标识符（如 POST-orders）

        Returns:
            文档路径
        """
        # 构建目录路径
        if doc_type == "api":
            dir_path = self.kb_path / "modules" / module / "apis"
        elif doc_type == "database":
            dir_path = self.kb_path / "modules" / module / "database"
        elif doc_type == "page":
            dir_path = self.kb_path / "modules" / module / "page"
        elif doc_type == "job":
            dir_path = self.kb_path / "modules" / module / "job"
        elif doc_type == "config":
            dir_path = self.kb_path / "modules" / module / "config"
        else:
            raise ValueError(f"不支持的文档类型: {doc_type}")

        # 创建目录
        dir_path.mkdir(parents=True, exist_ok=True)

        # 保存文档
        file_path = dir_path / f"{identifier}.md"
        file_path.write_text(content, encoding='utf-8')

        return str(file_path)


class DocGuardian:
    """文档填写助手主类"""

    def __init__(self, knowledge_base_path: str = "knowledge-base"):
        self.extractor = FieldExtractor()
        self.generator = DocTemplateGenerator(knowledge_base_path)

    def generate_api_doc_interactive(self, file_path: str, function_name: str) -> str:
        """
        交互式生成接口文档（命令行模式）

        Args:
            file_path: 接口文件路径（如 sevice/api/order.py）
            function_name: 函数名（如 create_order）

        Returns:
            生成的文档路径
        """
        # 1. 读取代码
        try:
            code = Path(file_path).read_text(encoding='utf-8')
        except Exception as e:
            return f"❌ 读取文件失败: {e}"

        # 2. 提取字段（预填充）
        fields = self.extractor.extract_api_fields(code, function_name)

        if "error" in fields:
            return f"❌ {fields['error']}"

        # 3. 显示预填充字段
        print(f"\n✅ 检测到接口：{fields['method']} {fields['path']}")
        print(f"✅ 接口描述：{fields['description'] or '（未填写 docstring）'}")
        print(f"\n✅ 已预填充以下字段：")
        print(f"   - 接口路径：{fields['path']}")
        print(f"   - 请求方法：{fields['method']}")

        if fields['request_params']:
            print(f"   - 请求参数：")
            for param, info in fields['request_params'].items():
                print(f"     • {param} ({info['type']})")
        else:
            print(f"   - 请求参数：无")

        # 4. 引导研发补充信息
        print(f"\n请补充以下信息：")

        # 模块名
        module = input("1. 模块名（如 order）: ").strip()
        if not module:
            module = "default"

        # 业务规则
        print("2. 业务规则（多条用分号分隔，直接回车跳过）: ")
        business_rules_input = input("> ").strip()
        business_rules = [r.strip() for r in business_rules_input.split(';') if r.strip()] if business_rules_input else []

        # 异常场景
        print("3. 异常场景（多条用分号分隔，直接回车跳过）: ")
        error_cases_input = input("> ").strip()
        error_cases = [e.strip() for e in error_cases_input.split(';') if e.strip()] if error_cases_input else []

        # 关联数据库表
        print("4. 关联数据库表（多个用逗号分隔，直接回车跳过）: ")
        related_db_input = input("> ").strip()
        related_db = [t.strip() for t in related_db_input.split(',') if t.strip()] if related_db_input else []

        # 关联前端页面
        print("5. 关联前端页面（多个用逗号分隔，直接回车跳过）: ")
        related_page_input = input("> ").strip()
        related_page = [p.strip() for p in related_page_input.split(',') if p.strip()] if related_page_input else []

        # 5. 生成文档
        user_input = {
            "module": module,
            "business_rules": business_rules,
            "error_cases": error_cases,
            "related_db": related_db,
            "related_page": related_page
        }

        doc_content = self.generator.generate_api_doc(fields, user_input)

        # 6. 保存文档
        identifier = f"{fields['method']}-{fields['path'].replace('/', '-').strip('-')}"
        doc_path = self.generator.save_doc("api", doc_content, module, identifier)

        print(f"\n✅ 文档已生成：{doc_path}")
        return doc_path

    def generate_api_doc_programmatic(self, file_path: str, function_name: str, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        程序化生成接口文档（MCP 工具模式，供 AI 调用）

        Args:
            file_path: 接口文件路径
            function_name: 函数名
            user_input: 研发补充的信息
                {
                    "module": "order",
                    "business_rules": ["订单金额必须 >0"],
                    "error_cases": ["库存不足返回 400"],
                    "related_db": ["t_order"],
          "related_page": ["OrderCreate.vue"]
                }

        Returns:
            {
                "success": True/False,
                "doc_path": "knowledge-base/modules/order/apis/POST-orders.md",
                "message": "文档已生成"
            }
        """
        try:
            # 1. 读取代码
            code = Path(file_path).read_text(encoding='utf-8')

            # 2. 提取字段
            fields = self.extractor.extract_api_fields(code, function_name)

            if "error" in fields:
                return {"success": False, "message": fields["error"]}

            # 3. 生成文档
            doc_content = self.generator.generate_api_doc(fields, user_input)

            # 4. 保存文档
            module = user_input.get("module", "default")
            identifier = f"{fields['method']}-{fields['path'].replace('/', '-').strip('-')}"
            doc_path = self.generator.save_doc("api", doc_content, module, identifier)

            return {
                "success": True,
                "doc_path": doc_path,
                "message": f"文档已生成：{doc_path}",
                "pre_filled_fields": {
                    "path": fields['path'],
                    "method": fields['method'],
                    "description": fields['description'],
                    "request_params": list(fields['request_params'].keys()) if fields['request_params'] else []
                }
            }

        except Exception as e:
            return {"success": False, "message": f"生成文档失败: {e}"}


# ============ CLI 入口 ============

def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="文档填写助手（DocGuardian）")
    parser.add_argument("command", choices=["api", "database", "page"], help="文档类型")
    parser.add_argument("--file", required=True, help="代码文件路径")
    parser.add_argument("--function", help="函数名（api 类型必填）")
    parser.add_argument("--kb-path", default="knowledge-base", help="知识库路径")

    args = parser.parse_args()

    guardian = DocGuardian(knowledge_base_path=args.kb_path)

    if args.command == "api":
        if not args.function:
            print("❌ 错误：api 类型必须指定 --function 参数")
            return

        guardian.generate_api_doc_interactive(args.file, args.function)
    else:
        print(f"❌ 暂不支持 {args.command} 类型（开发中）")


if __name__ == "__main__":
    main()
