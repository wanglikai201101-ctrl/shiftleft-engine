"""
DocGuardian MCP 工具封装

将 DocGuardian 封装为 MCP 工具，供 AI 调用。
研发可以通过自然语言调用："帮我生成接口文档"

作者：示例团队
创建时间：2025-04-20
"""

from typing import Dict, Any
from .doc_guardian import DocGuardian


# 全局实例
_guardian = DocGuardian()


def generate_api_doc(
    file_path: str,
    function_name: str,
    module: str,
    business_rules: list = None,
    error_cases: list = None,
    related_db: list = None,
    related_page: list = None
) -> Dict[str, Any]:
    """
    生成接口文档（MCP 工具）
    
    Args:
        file_path: 接口文件路径（如 sevice/api/order.py）
        function_name: 函数名（如 create_order）
        module: 模块名（如 order）
        business_rules: 业务规则列表（如 ["订单金额必须 >0", "订单明细不能为空"]）
        error_cases: 异常场景列表（如 ["库存不足返回 400", "用户余额不足返回 402"]）
        related_db: 关联数据库表列表（如 ["t_order", "t_order_item"]）
        related_page: 关联前端页面列表（如 ["OrderCreate.vue"]）
    
    Returns:
        {
            "success": True/False,
            "doc_path": "knowledge-base/modules/order/apis/POST-orders.md",
            "message": "文档已生成",
            "pre_filled_fields": {
                "path": "/orders",
                "method": "POST",
                "description": "创建订单",
                "request_params": ["order_no", "amount", "items"]
            }
        }
    
    Example:
        研发：帮我生成 create_order 接口的文档
        
        AI：好的，我需要你补充一些信息：
        1. 模块名是什么？
        2. 业务规则有哪些？
        3. 异常场景有哪些？
        
        研发：模块名是 order，业务规则是订单金额必须 >0，异常场景是库存不足返回 400
        
        AI：[调用 generate_api_doc]
        ✅ 文档已生成：knowledge-base/modules/order/apis/POST-orders.md
    """
    user_input = {
        "module": module,
        "business_rules": business_rules or [],
        "error_cases": error_cases or [],
        "related_db": related_db or [],
        "related_page": related_page or []
    }
    
    return _guardian.generate_api_doc_programmatic(file_path, function_name, user_input)


def get_api_info(file_path: str, function_name: str) -> Dict[str, Any]:
    """
    获取接口信息（预填充字段）
    
    用于 AI 先展示预填充字段，再引导研发补充信息。
    
    Args:
        file_path: 接口文件路径
        function_name: 函数名
    
    Returns:
        {
            "success": True/False,
            "fields": {
                "path": "/orders",
                "method": "POST",
                "description": "创建订单",
                "request_params": {
                    "order_no": {"type": "string", "required": True},
                    "amount": {"type": "number", "required": True}
                }
            },
            "message": "已提取接口信息"
        }

    Example:
        研发：帮我生成 create_order 接口的文档

        AI：[调用 get_api_info]
        ✅ 检测到接口：POST /orders
        ✅ 已预填充以下字段：
           - 接口路径：/orders
           - 请求方法：POST
           - 请求参数：order_no(string), amount(number)

        请补充：
        1. 模块名
        2. 业务规则
        3. 异常场景
    """
    try:
        from pathlib import Path
        code = Path(file_path).read_text(encoding='utf-8')
        fields = _guardian.extractor.extract_api_fields(code, function_name)
        
        if "error" in fields:
            return {"success": False, "message": fields["error"]}
        
        return {
            "success": True,
            "fields": fields,
            "message": "已提取接口信息"
        }
    
    except Exception as e:
        return {"success": False, "message": f"提取接口信息失败: {e}"}


# MCP 工具注册（如果需要）
MCP_TOOLS = [
    {
        "name": "generate_api_doc",
        "description": "生成接口文档到 knowledge-base",
        "function": generate_api_doc
    },
    {
        "name": "get_api_info",
        "description": "获取接口信息（预填充字段）",
        "function": get_api_info
    }
]
