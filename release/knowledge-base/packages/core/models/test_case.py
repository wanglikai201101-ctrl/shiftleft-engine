"""测试用例数据模型"""

from dataclasses import dataclass


@dataclass
class TestCase:
    """测试用例"""
    name: str
    description: str
    test_type: str  # success, error, boundary, concurrent
    code_template: str
