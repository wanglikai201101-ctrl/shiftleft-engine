"""测试用例骨架生成器：从文档推导测试用例"""

import re
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from ..models.test_case import TestCase


class TestDerivationRules:
    """测试推导规则库"""

    @staticmethod
    def derive_from_field_type(field_name: str, field_type: str) -> List[TestCase]:
        cases = []
        if "varchar" in field_type.lower():
            match = re.search(r"varchar\((\d+)\)", field_type, re.IGNORECASE)
            if match:
                n = int(match.group(1))
                cases.append(TestCase(
                    name=f"test_{field_name}_boundary",
                    description=f"测试 {field_name} 字段边界值（长度 {n}）",
                    test_type="boundary",
                    code_template=f"""
    def test_{field_name}_boundary(self):
        \"\"\"测试 {field_name} 字段边界值（长度 {n}）\"\"\"
        data = {{{field_name!r}: 'a' * {n - 1}}}  # 正常
        data = {{{field_name!r}: 'a' * {n}}}      # 边界
        data = {{{field_name!r}: 'a' * {n + 1}}}  # 超出，预期失败
        pass
""",
                ))
        if field_type.lower() in ("int", "bigint", "integer"):
            cases.append(TestCase(
                name=f"test_{field_name}_boundary",
                description=f"测试 {field_name} 字段边界值",
                test_type="boundary",
                code_template=f"""
    def test_{field_name}_boundary(self):
        \"\"\"测试 {field_name} 字段边界值\"\"\"
        # 正常值 / 负数 / 零
        pass
""",
            ))
        return cases

    @staticmethod
    def derive_from_unique_index(table_name: str, field_name: str) -> List[TestCase]:
        return [TestCase(
            name=f"test_{table_name}_{field_name}_unique",
            description=f"测试 {table_name}.{field_name} 唯一性约束",
            test_type="error",
            code_template=f"""
    def test_{table_name}_{field_name}_unique(self):
        \"\"\"测试 {table_name}.{field_name} 唯一性约束\"\"\"
        # 插入第一条 → 成功；插入重复 → 预期失败
        pass
""",
        )]

    @staticmethod
    def derive_from_version_field(table_name: str) -> List[TestCase]:
        return [TestCase(
            name=f"test_{table_name}_concurrent_update",
            description=f"测试 {table_name} 并发更新（乐观锁）",
            test_type="concurrent",
            code_template=f"""
    def test_{table_name}_concurrent_update(self):
        \"\"\"测试 {table_name} 并发更新（乐观锁）\"\"\"
        # 两个请求同时更新同一条记录，一个成功一个失败
        pass
""",
        )]

    @staticmethod
    def derive_from_status_field(field_name: str, status_values: List[str]) -> List[TestCase]:
        return [TestCase(
            name=f"test_{field_name}_transitions",
            description=f"测试 {field_name} 状态转换",
            test_type="success",
            code_template=f"""
    def test_{field_name}_valid_transitions(self):
        \"\"\"测试 {field_name} 合法状态转换\"\"\"
        pass

    def test_{field_name}_invalid_transitions(self):
        \"\"\"测试 {field_name} 非法状态转换\"\"\"
        pass
""",
        )]


class ApiTestGenerator:
    """从接口文档生成 API 测试骨架"""

    def generate(self, api_doc_path: str) -> str:
        content = Path(api_doc_path).read_text(encoding="utf-8")
        api_info = self._parse_api_doc(content)
        test_cases = [self._success_case(api_info)]
        test_cases.extend(self._error_cases(api_info))
        return self._render(api_info, test_cases)

    def _parse_api_doc(self, content: str) -> Dict:
        info = {"method": "", "path": "", "description": "", "error_scenarios": []}
        m = re.search(r"(GET|POST|PUT|DELETE|PATCH)\s+(/[^\s]+)", content)
        if m:
            info["method"], info["path"] = m.group(1), m.group(2)
        m = re.search(r"##\s*接口描述\s*\n\s*(.+)", content)
        if m:
            info["description"] = m.group(1).strip()
        err = re.search(r"##\s*异常场景\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
        if err:
            for line in err.group(1).strip().split("\n"):
                line = line.strip()
                if line.startswith("-") or line.startswith("*"):
                    info["error_scenarios"].append(line[1:].strip())
        return info

    def _success_case(self, info: Dict) -> TestCase:
        method = info["method"].lower()
        path_id = info["path"].replace("/", "_").replace("{", "").replace("}", "")
        return TestCase(
            name=f"test_{method}{path_id}_success",
            description=f"正常场景：{info['description']}",
            test_type="success",
            code_template=f"""
    def test_{method}{path_id}_success(self):
        \"\"\"正常场景：{info['description']}\"\"\"
        # TODO: 准备数据、调用接口、断言
        pass
""",
        )

    def _error_cases(self, info: Dict) -> List[TestCase]:
        cases = []
        method = info["method"].lower()
        path_id = info["path"].replace("/", "_").replace("{", "").replace("}", "")
        for i, scenario in enumerate(info["error_scenarios"], 1):
            cases.append(TestCase(
                name=f"test_{method}{path_id}_error_{i}",
                description=f"异常场景：{scenario}",
                test_type="error",
                code_template=f"""
    def test_{method}{path_id}_error_{i}(self):
        \"\"\"异常场景：{scenario}\"\"\"
        # TODO: 准备异常数据、调用接口、断言
        pass
""",
            ))
        return cases

    def _render(self, info: Dict, cases: List[TestCase]) -> str:
        method = info["method"].lower()
        path_id = info["path"].replace("/", "_").replace("{", "").replace("}", "")
        class_name = f"Test{method.capitalize()}{path_id.replace('_', '').title()}"
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        code = f'"""\n测试 {info["method"]} {info["path"]} - {info["description"]}\n\n自动生成时间：{ts}\n"""\n\nimport pytest\n\n\nclass {class_name}:\n    """测试 {info["method"]} {info["path"]}"""\n'
        for c in cases:
            code += c.code_template
        return code


class DatabaseTestGenerator:
    """从数据库文档生成数据库测试骨架"""

    def generate(self, db_doc_path: str) -> str:
        content = Path(db_doc_path).read_text(encoding="utf-8")
        db_info = self._parse(db_doc_path, content)
        rules = TestDerivationRules()
        cases = []
        for f in db_info["fields"]:
            cases.extend(rules.derive_from_field_type(f["name"], f["type"]))
        for idx in db_info["unique_indexes"]:
            cases.extend(rules.derive_from_unique_index(db_info["table_name"], idx))
        if db_info["has_version"]:
            cases.extend(rules.derive_from_version_field(db_info["table_name"]))
        for sf in db_info["status_fields"]:
            cases.extend(rules.derive_from_status_field(sf["name"], sf["values"]))
        return self._render(db_info, cases)

    def _parse(self, doc_path: str, content: str) -> Dict:
        info = {"table_name": "", "fields": [], "unique_indexes": [], "has_version": False, "status_fields": []}
        name = Path(doc_path).stem
        if name.startswith("db-"):
            info["table_name"] = name[3:]
        info["has_version"] = "version" in content.lower()
        return info

    def _render(self, info: Dict, cases: List[TestCase]) -> str:
        table = info["table_name"]
        class_name = f"Test{table.replace('_', '').title()}"
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        code = f'"""\n测试数据库表 {table}\n\n自动生成时间：{ts}\n"""\n\nimport pytest\n\n\nclass {class_name}:\n    """测试数据库表 {table}"""\n'
        for c in cases:
            code += c.code_template
        return code
