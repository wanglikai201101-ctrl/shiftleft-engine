"""
测试用例自动生成工具（TestGenerator）

从文档自动生成测试用例骨架，减少测试编写工作量。

功能：
1. 从接口文档生成 API 测试用例
2. 从数据库文档生成数据库测试用例
3. 基于推导规则自动生成测试场景

使用方式：
1. 生成接口测试：python -m tools.knowledge_base.test_generator api --doc path/to/api.md --output tests/test_api.py
2. 生成数据库测试：python -m tools.knowledge_base.test_generator database --doc path/to/db.md --output tests/test_db.py

作者：示例团队
创建时间：2025-04-22
"""

import re
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class TestCase:
    """测试用例"""
    name: str
    description: str
    test_type: str  # success, error, boundary, concurrent
    code_template: str


class TestDerivationRules:
    """测试推导规则库"""

    @staticmethod
    def derive_from_field_type(field_name: str, field_type: str) -> List[TestCase]:
        """从字段类型推导测试用例"""
        cases = []

        # varchar(N) -> 边界值测试
        if 'varchar' in field_type.lower():
            match = re.search(r'varchar\((\d+)\)', field_type, re.IGNORECASE)
            if match:
                max_len = int(match.group(1))
                cases.append(TestCase(
                    name=f"test_{field_name}_boundary",
                    description=f"测试 {field_name} 字段边界值",
                    test_type="boundary",
                    code_template=f"""
    def test_{field_name}_boundary(self):
        \"\"\"测试 {field_name} 字段边界值（长度 {max_len}）\"\"\"
        # 正常：{max_len-1} 字符
        data = {{{field_name!r}: 'a' * {max_len-1}}}
        # TODO: 调用接口或数据库操作

        # 边界：{max_len} 字符
        data = {{{field_name!r}: 'a' * {max_len}}}
        # TODO: 调用接口或数据库操作

        # 超出：{max_len+1} 字符
        data = {{{field_name!r}: 'a' * {max_len+1}}}
        # TODO: 预期失败
"""
                ))

        # int/bigint -> 边界值测试
        if field_type.lower() in ['int', 'bigint', 'integer']:
            cases.append(TestCase(
                name=f"test_{field_name}_boundary",
                description=f"测试 {field_name} 字段边界值",
                test_type="boundary",
                code_template=f"""
    def test_{field_name}_boundary(self):
        \"\"\"测试 {field_name} 字段边界值\"\"\"
        # 正常值
        data = {{{field_name!r}: 100}}
        # TODO: 调用接口或数据库操作

        # 负数
        data = {{{field_name!r}: -1}}
        # TODO: 根据业务规则判断是否允许

        # 零
        data = {{{field_name!r}: 0}}
        # TODO: 根据业务规则判断是否允许
"""
            ))

        return cases

    @staticmethod
    def derive_from_status_field(field_name: str, status_values: List[str]) -> List[TestCase]:
        """从状态字段推导状态机测试"""
        cases = []

        # 生成状态转换测试
        cases.append(TestCase(
            name=f"test_{field_name}_transitions",
            description=f"测试 {field_name} 状态转换",
            test_type="success",
            code_template=f"""
    def test_{field_name}_valid_transitions(self):
        \"\"\"测试 {field_name} 合法状态转换\"\"\"
        # TODO: 根据状态流转图实现
        # 例如：pending -> processing -> completed
        pass

    def test_{field_name}_invalid_transitions(self):
        \"\"\"测试 {field_name} 非法状态转换\"\"\"
        # TODO: 测试所有非法状态跳转
        # 例如：completed -> pending（不允许）
        pass
"""
        ))

        return cases

    @staticmethod
    def derive_from_unique_index(table_name: str, field_name: str) -> List[TestCase]:
        """从唯一索引推导唯一性测试"""
        return [TestCase(
            name=f"test_{table_name}_{field_name}_unique",
            description=f"测试 {table_name}.{field_name} 唯一性约束",
            test_type="error",
            code_template=f"""
    def test_{table_name}_{field_name}_unique(self):
        \"\"\"测试 {table_name}.{field_name} 唯一性约束\"\"\"
        # 插入第一条记录
        data1 = {{{field_name!r}: 'test_value'}}
        # TODO: 插入数据

        # 尝试插入重复记录
        data2 = {{{field_name!r}: 'test_value'}}
        # TODO: 预期失败（唯一性冲突）
"""
        )]

    @staticmethod
    def derive_from_version_field(table_name: str) -> List[TestCase]:
        """从乐观锁字段推导并发测试"""
        return [TestCase(
            name=f"test_{table_name}_concurrent_update",
            description=f"测试 {table_name} 并发更新（乐观锁）",
            test_type="concurrent",
            code_template=f"""
    def test_{table_name}_concurrent_update(self):
        \"\"\"测试 {table_name} 并发更新（乐观锁）\"\"\"
        # 读取记录（version=1）
        # TODO: 查询记录

        # 两个请求同时更新
        # 请求1：version=1 -> version=2（成功）
        # 请求2：version=1 -> version=2（失败，version 已变化）
        # TODO: 实现并发测试逻辑
"""
        )]


class ApiTestGenerator:
    """接口测试生成器"""

    def generate(self, api_doc_path: str) -> str:
        """
        从接口文档生成测试用例

        Args:
            api_doc_path: 接口文档路径

        Returns:
            测试代码
        """
        # 1. 解析接口文档
        api_info = self._parse_api_doc(api_doc_path)

        # 2. 生成测试用例
        test_cases = []

        # 正常场景
        test_cases.append(self._generate_success_case(api_info))

        # 异常场景（从文档的"异常场景"部分提取）
        test_cases.extend(self._generate_error_cases(api_info))

        # 边界值测试（从请求参数推导）
        test_cases.extend(self._generate_boundary_cases(api_info))

        # 3. 生成测试文件
        return self._render_test_file(api_info, test_cases)

    def _parse_api_doc(self, doc_path: str) -> Dict:
        """解析接口文档"""
        content = Path(doc_path).read_text(encoding='utf-8')

        api_info = {
            'method': '',
            'path': '',
            'description': '',
            'request_params': [],
            'response_fields': [],
            'error_scenarios': [],
            'business_rules': []
        }

        # 提取接口方法和路径（如 POST /orders）
        method_match = re.search(r'(GET|POST|PUT|DELETE|PATCH)\s+(/[^\s]+)', content)
        if method_match:
            api_info['method'] = method_match.group(1)
            api_info['path'] = method_match.group(2)

        # 提取描述
        desc_match = re.search(r'##\s*接口描述\s*\n\s*(.+)', content)
        if desc_match:
            api_info['description'] = desc_match.group(1).strip()

        # 提取请求参数
        # TODO: 解析请求参数表格

        # 提取异常场景
        error_section = re.search(r'##\s*异常场景\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
        if error_section:
            error_lines = error_section.group(1).strip().split('\n')
            for line in error_lines:
                if line.strip().startswith('-') or line.strip().startswith('*'):
                    api_info['error_scenarios'].append(line.strip()[1:].strip())

        return api_info

    def _generate_success_case(self, api_info: Dict) -> TestCase:
        """生成正常场景测试用例"""
        method = api_info['method'].lower()
        path = api_info['path'].replace('/', '_').replace('{', '').replace('}', '')

        return TestCase(
            name=f"test_{method}{path}_success",
            description=f"正常场景：{api_info['description']}",
            test_type="success",
            code_template=f"""
    def test_{method}{path}_success(self):
        \"\"\"正常场景：{api_info['description']}\"\"\"
        # TODO: 准备测试数据
        data = {{}}

        # TODO: 调用接口
        # response = requests.{method}('{api_info['path']}', json=data)

        # TODO: 断言
        # assert response.status_code == 200
        pass
"""
        )

    def _generate_error_cases(self, api_info: Dict) -> List[TestCase]:
        """生成异常场景测试用例"""
        cases = []

        for i, scenario in enumerate(api_info['error_scenarios'], 1):
            method = api_info['method'].lower()
            path = api_info['path'].replace('/', '_').replace('{', '').replace('}', '')

            cases.append(TestCase(
                name=f"test_{method}{path}_error_{i}",
                description=f"异常场景：{scenario}",
                test_type="error",
                code_template=f"""
    def test_{method}{path}_error_{i}(self):
        \"\"\"异常场景：{scenario}\"\"\"
        # TODO: 准备异常数据
        data = {{}}

        # TODO: 调用接口
        # response = requests.{method}('{api_info['path']}', json=data)

        # TODO: 断言
        # assert response.status_code == 400
        pass
"""
            ))

        return cases

    def _generate_boundary_cases(self, api_info: Dict) -> List[TestCase]:
        """生成边界值测试用例"""
        # TODO: 从请求参数推导边界值测试
        return []

    def _render_test_file(self, api_info: Dict, test_cases: List[TestCase]) -> str:
        """渲染测试文件"""
        method = api_info['method'].lower()
        path = api_info['path'].replace('/', '_').replace('{', '').replace('}', '')
        class_name = f"Test{method.capitalize()}{path.replace('_', '').title()}"

        code = f'''"""
测试 {api_info['method']} {api_info['path']} - {api_info['description']}

自动生成时间：{self._get_timestamp()}
来源文档：接口文档
"""

import pytest


class {class_name}:
    """测试 {api_info['method']} {api_info['path']} - {api_info['description']}"""
'''

        for case in test_cases:
            code += case.code_template

        return code

    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


class DatabaseTestGenerator:
    """数据库测试生成器"""

    def generate(self, db_doc_path: str) -> str:
        """
        从数据库文档生成测试用例

        Args:
            db_doc_path: 数据库文档路径

        Returns:
            测试代码
        """
        # 1. 解析数据库文档
        db_info = self._parse_db_doc(db_doc_path)

        # 2. 生成测试用例
        test_cases = []
        rules = TestDerivationRules()

        # 从字段类型推导
        for field in db_info['fields']:
            test_cases.extend(rules.derive_from_field_type(field['name'], field['type']))

        # 从唯一索引推导
        for index in db_info['unique_indexes']:
            test_cases.extend(rules.derive_from_unique_index(db_info['table_name'], index))

        # 从乐观锁字段推导
        if db_info['has_version']:
            test_cases.extend(rules.derive_from_version_field(db_info['table_name']))

        # 从状态字段推导
        for status_field in db_info['status_fields']:
            test_cases.extend(rules.derive_from_status_field(
                status_field['name'],
                status_field['values']
            ))

        # 3. 生成测试文件
        return self._render_test_file(db_info, test_cases)

    def _parse_db_doc(self, doc_path: str) -> Dict:
        """解析数据库文档"""
        content = Path(doc_path).read_text(encoding='utf-8')

        db_info = {
            'table_name': '',
            'fields': [],
            'unique_indexes': [],
            'has_version': False,
            'status_fields': []
        }

        # 提取表名（从文件名或文档标题）
        doc_name = Path(doc_path).stem
        if doc_name.startswith('db-'):
            db_info['table_name'] = doc_name[3:]

        # 提取字段信息（从表格）
        # TODO: 解析字段表格

        # 检查是否有 version 字段
        if 'version' in content.lower():
            db_info['has_version'] = True

        return db_info

    def _render_test_file(self, db_info: Dict, test_cases: List[TestCase]) -> str:
        """渲染测试文件"""
        table_name = db_info['table_name']
        class_name = f"Test{table_name.replace('_', '').title()}"

        code = f'''"""
测试数据库表 {table_name}

自动生成时间：{self._get_timestamp()}
来源文档：数据库文档
"""

import pytest


class {class_name}:
    """测试数据库表 {table_name}"""
'''

        for case in test_cases:
            code += case.code_template

        return code

    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 5:
        print("用法:")
        print("  python -m tools.knowledge_base.test_generator api --doc <doc_path> --output <output_path>")
        print("  python -m tools.knowledge_base.test_generator database --doc <doc_path> --output <output_path>")
        sys.exit(1)

    test_type = sys.argv[1]
    doc_path = sys.argv[3]
    output_path = sys.argv[5]

    if test_type == "api":
        generator = ApiTestGenerator()
        code = generator.generate(doc_path)
    elif test_type == "database":
        generator = DatabaseTestGenerator()
        code = generator.generate(doc_path)
    else:
        print(f"不支持的测试类型: {test_type}")
        sys.exit(1)

    # 保存测试文件
    Path(output_path).write_text(code, encoding='utf-8')
    print(f"✅ 测试文件已生成: {output_path}")
