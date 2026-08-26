"""
文档一致性检查工具（DocLinter）

检查文档与代码的一致性，确保文档内容与实际代码保持同步。

功能：
1. 检查页面文档中的 data-testid 是否在 Vue 代码中存在
2. 检查接口文档的"需求来源"是否在需求文档中存在
3. 检查数据库文档的字段是否与 DDL 一致
4. 检查双向引用的完整性

使用方式：
1. 检查单个文档：python -m tools.knowledge_base.doc_linter check --doc path/to/doc.md
2. 检查整个模块：python -m tools.knowledge_base.doc_linter check-module --module order
3. 检查所有文档：python -m tools.knowledge_base.doc_linter check-all

作者：示例团队
创建时间：2025-04-22
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class Severity(Enum):
    """问题严重程度"""
    ERROR = "❌ 错误"
    WARNING = "⚠️  警告"
    INFO = "ℹ️  信息"


@dataclass
class LintIssue:
    """检查问题"""
    severity: Severity
    doc_path: str
    message: str
    line_number: Optional[int] = None


class PageTestIdChecker:
    """页面 data-testid 检查器（支持 Vue/React/HTML/JSX 等）"""

    def check(self, page_doc_path: str, frontend_file_path: str) -> List[LintIssue]:
        """
        检查页面文档中的 data-testid 是否在前端代码中存在

        Args:
            page_doc_path: 页面文档路径
            frontend_file_path: 前端文件路径（.vue/.jsx/.tsx/.html 等）

        Returns:
            问题列表
        """
        issues = []

        # 1. 从文档中提取 data-testid
        doc_testids = self._extract_testids_from_doc(page_doc_path)

        # 2. 从前端文件中提取 data-testid
        code_testids = self._extract_testids_from_code(frontend_file_path)

        # 3. 对比差异
        missing_in_code = doc_testids - code_testids
        missing_in_doc = code_testids - doc_testids

        for testid in missing_in_code:
            issues.append(LintIssue(
                severity=Severity.ERROR,
                doc_path=page_doc_path,
                message=f'data-testid "{testid}" 在文档中存在，但在代码 {frontend_file_path} 中未找到'
            ))

        for testid in missing_in_doc:
            issues.append(LintIssue(
                severity=Severity.WARNING,
                doc_path=page_doc_path,
                message=f'data-testid "{testid}" 在代码中存在，但在文档中未记录'
            ))

        return issues

    def _extract_testids_from_doc(self, doc_path: str) -> set:
        """从文档中提取 data-testid"""
        try:
            content = Path(doc_path).read_text(encoding='utf-8')
        except Exception:
            return set()

        # 匹配表格中的 data-testid（如 | order-create-btn-submit | 提交按钮 |）
        pattern = r'\|\s*([a-z0-9\-]+)\s*\|'
        matches = re.findall(pattern, content)

        # 过滤掉表头和非 testid 的内容
        testids = {m for m in matches if '-' in m and not m.startswith('---')}

        return testids

    def _extract_testids_from_code(self, file_path: str) -> set:
        """
        从前端代码中提取 data-testid
        支持多种格式：
        - Vue: data-testid="xxx" 或 :data-testid="xxx"
        - React/JSX: data-testid="xxx" 或 data-testid={xxx}
        - HTML: data-testid="xxx"
        """
        try:
            content = Path(file_path).read_text(encoding='utf-8')
        except Exception:
            return set()

        testids = set()

        # 模式1: data-testid="xxx" 或 :data-testid="xxx" (Vue/HTML)
        pattern1 = r':?data-testid=["\']([^"\']+)["\']'
        testids.update(re.findall(pattern1, content))

        # 模式2: data-testid={xxx} (React/JSX)
        pattern2 = r'data-testid=\{["\']?([^}"\']+)["\']?\}'
        testids.update(re.findall(pattern2, content))

        # 模式3: data-testid={`xxx`} (React 模板字符串)
        pattern3 = r'data-testid=\{`([^`]+)`\}'
        testids.update(re.findall(pattern3, content))

        return testids


class RequirementSourceChecker:
    """需求来源检查器"""

    def __init__(self, knowledge_base_path: str = "knowledge-base"):
        self.kb_path = Path(knowledge_base_path)

    def check(self, api_doc_path: str) -> List[LintIssue]:
        """
        检查接口文档的"需求来源"是否在需求文档中存在

        Args:
            api_doc_path: 接口文档路径

        Returns:
            问题列表
        """
        issues = []

        # 1. 从接口文档中提取需求来源
        req_ids = self._extract_requirement_ids(api_doc_path)

        # 2. 检查每个需求文档是否存在
        for req_id in req_ids:
            if not self._requirement_exists(req_id):
                issues.append(LintIssue(
                    severity=Severity.ERROR,
                    doc_path=api_doc_path,
                    message=f'需求来源 {req_id} 的文档不存在'
                ))

        return issues

    def _extract_requirement_ids(self, doc_path: str) -> List[str]:
        """从文档中提取需求 ID（如 REQ-001）"""
        try:
            content = Path(doc_path).read_text(encoding='utf-8')
        except Exception:
            return []

        # 匹配 REQ-xxx 格式
        pattern = r'REQ-\d{3}'
        matches = re.findall(pattern, content)

        return matches

    def _requirement_exists(self, req_id: str) -> bool:
        """检查需求文档是否存在"""
        # 在 knowledge-base 目录下搜索需求文档
        # 支持多种路径格式：
        # - modules/*/requirements/REQ-001.md
        # - requirements/REQ-001.md

        patterns = [
            f"modules/*/requirements/{req_id}.md",
            f"requirements/{req_id}.md",
        ]

        for pattern in patterns:
            matches = list(self.kb_path.glob(pattern))
            if matches:
                return True

        return False


class DatabaseFieldChecker:
    """数据库字段检查器"""

    def check(self, db_doc_path: str, ddl_file_path: str) -> List[LintIssue]:
        """
        检查数据库文档的字段是否与 DDL 一致

        Args:
            db_doc_path: 数据库文档路径
            ddl_file_path: DDL 文件路径

        Returns:
            问题列表
        """
        issues = []

        # 1. 从文档中提取字段
        doc_fields = self._extract_fields_from_doc(db_doc_path)

        # 2. 从 DDL 中提取字段
        ddl_fields = self._extract_fields_from_ddl(ddl_file_path)

        # 3. 对比差异
        missing_in_doc = ddl_fields - doc_fields
        missing_in_ddl = doc_fields - ddl_fields

        for field in missing_in_doc:
            issues.append(LintIssue(
                severity=Severity.WARNING,
                doc_path=db_doc_path,
                message=f'字段 "{field}" 在 DDL 中存在，但在文档中未记录'
            ))

        for field in missing_in_ddl:
            issues.append(LintIssue(
                severity=Severity.ERROR,
                doc_path=db_doc_path,
                message=f'字段 "{field}" 在文档中存在，但在 DDL {ddl_file_path} 中未找到'
            ))

        return issues

    def _extract_fields_from_doc(self, doc_path: str) -> set:
        """从文档中提取字段名"""
        try:
            content = Path(doc_path).read_text(encoding='utf-8')
        except Exception:
            return set()

        # 匹配表格中的字段名（第一列）
        # | 字段名 | 类型 | 索引 | ...
        # | id | bigint | PK | ...
        lines = content.split('\n')
        fields = set()

        in_table = False
        for line in lines:
            if '|' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 3:
                    # 跳过表头和分隔线
                    if parts[1] in ['字段', '字段名', 'Field', '---', '']:
                        in_table = True
                        continue

                    if in_table and parts[1]:
                        fields.add(parts[1])
            else:
                in_table = False

        return fields

    def _extract_fields_from_ddl(self, ddl_path: str) -> set:
        """从 DDL 中提取字段名"""
        try:
            content = Path(ddl_path).read_text(encoding='utf-8')
        except Exception:
            return set()

        # 匹配 CREATE TABLE 中的字段定义
        # `field_name` type ...
        pattern = r'`([a-z_]+)`\s+\w+'
        matches = re.findall(pattern, content, re.IGNORECASE)

        return set(matches)


class BidirectionalRefChecker:
    """双向引用检查器"""

    def __init__(self, knowledge_base_path: str = "knowledge-base"):
        self.kb_path = Path(knowledge_base_path)

    def check(self, doc_path: str) -> List[LintIssue]:
        """
        检查双向引用的完整性

        例如：
        - 需求文档引用了接口 A，检查接口 A 是否引用了该需求
        - 接口文档引用了表 B，检查表 B 是否引用了该接口

        Args:
            doc_path: 文档路径

        Returns:
            问题列表
        """
        issues = []

        # 1. 提取当前文档的所有引用
        references = self._extract_references(doc_path)

        # 2. 检查每个引用的反向引用
        for ref_type, ref_path in references:
            if not self._has_reverse_reference(doc_path, ref_path):
                issues.append(LintIssue(
                    severity=Severity.WARNING,
                    doc_path=doc_path,
                    message=f'引用了 {ref_path}，但对方未反向引用本文档'
                ))

        return issues

    def _extract_references(self, doc_path: str) -> List[Tuple[str, str]]:
        """提取文档中的所有引用"""
        try:
            content = Path(doc_path).read_text(encoding='utf-8')
        except Exception:
            return []

        references = []

        # 匹配 Markdown 链接：[text](path/to/file.md)
        pattern = r'\[([^\]]+)\]\(([^\)]+\.md)\)'
        matches = re.findall(pattern, content)

        for text, path in matches:
            # 判断引用类型
            if 'api' in path or 'API' in path:
                ref_type = 'api'
            elif 'requirement' in path or 'REQ' in path:
                ref_type = 'requirement'
            elif 'storage' in path or 'database' in path:
                ref_type = 'storage'
            elif 'page' in path:
                ref_type = 'page'
            else:
                ref_type = 'unknown'

            references.append((ref_type, path))

        return references

    def _has_reverse_reference(self, source_doc: str, target_doc: str) -> bool:
        """检查目标文档是否反向引用了源文档"""
        # 构建目标文档的完整路径
        source_path = Path(source_doc)
        target_path = self.kb_path / target_doc

        if not target_path.exists():
            return False

        try:
            content = target_path.read_text(encoding='utf-8')
        except Exception:
            return False

        # 检查目标文档是否包含源文档的文件名
        source_filename = source_path.name
        return source_filename in content


class DocLinter:
    """文档一致性检查器（主类）"""

    def __init__(self, knowledge_base_path: str = "knowledge-base"):
        self.kb_path = Path(knowledge_base_path)
        self.page_checker = PageTestIdChecker()
        self.req_checker = RequirementSourceChecker(knowledge_base_path)
        self.db_checker = DatabaseFieldChecker()
        self.ref_checker = BidirectionalRefChecker(knowledge_base_path)

    def check_document(self, doc_path: str) -> List[LintIssue]:
        """
        检查单个文档

        Args:
            doc_path: 文档路径（相对于 knowledge-base/）

        Returns:
            问题列表
        """
        issues = []
        full_path = self.kb_path / doc_path

        if not full_path.exists():
            return [LintIssue(
                severity=Severity.ERROR,
                doc_path=doc_path,
                message=f'文档不存在: {full_path}'
            )]

        # 根据文档类型选择检查器
        if 'page' in doc_path.lower():
            # 页面文档：检查 data-testid
            vue_file = self._find_vue_file(doc_path)
            if vue_file:
                issues.extend(self.page_checker.check(str(full_path), vue_file))

        elif 'api' in doc_path.lower():
            # 接口文档：检查需求来源
            issues.extend(self.req_checker.check(str(full_path)))

        elif 'storage' in doc_path.lower() or 'db-' in doc_path.lower():
            # 数据库文档：检查字段
            ddl_file = self._find_ddl_file(doc_path)
            if ddl_file:
                issues.extend(self.db_checker.check(str(full_path), ddl_file))

        # 所有文档：检查双向引用
        issues.extend(self.ref_checker.check(str(full_path)))

        return issues

    def check_module(self, module_name: str) -> Dict[str, List[LintIssue]]:
        """
        检查整个模块的所有文档

        Args:
            module_name: 模块名（如 "order"）

        Returns:
            {文档路径: 问题列表}
        """
        results = {}
        module_path = self.kb_path / "modules" / module_name

        if not module_path.exists():
            return {module_name: [LintIssue(
                severity=Severity.ERROR,
                doc_path=module_name,
                message=f'模块目录不存在: {module_path}'
            )]}

        # 扫描模块下的所有 MD 文档
        for md_file in module_path.rglob("*.md"):
            relative_path = str(md_file.relative_to(self.kb_path))
            issues = self.check_document(relative_path)
            if issues:
                results[relative_path] = issues

        return results

    def check_all(self) -> Dict[str, List[LintIssue]]:
        """
        检查所有文档

        Returns:
            {文档路径: 问题列表}
        """
        results = {}

        # 扫描 knowledge-base 下的所有 MD 文档
        for md_file in self.kb_path.rglob("*.md"):
            relative_path = str(md_file.relative_to(self.kb_path))
            issues = self.check_document(relative_path)
            if issues:
                results[relative_path] = issues

        return results

    def _find_vue_file(self, page_doc_path: str) -> Optional[str]:
        """根据页面文档路径查找对应的 Vue 文件"""
        # 从文档路径推导 Vue 文件路径
        # 例如：modules/order/pages/order-create.md -> src/pages/OrderCreate.vue

        doc_path = Path(page_doc_path)
        filename = doc_path.stem  # order-create

        # 转换为 PascalCase
        vue_name = ''.join(word.capitalize() for word in filename.split('-'))

        # 搜索可能的 Vue 文件路径
        possible_paths = [
            f"src/pages/{vue_name}.vue",
            f"src/views/{vue_name}.vue",
            f"frontend/src/pages/{vue_name}.vue",
            f"frontend/src/views/{vue_name}.vue",
        ]

        for path in possible_paths:
            if Path(path).exists():
                return path

        return None

    def _find_ddl_file(self, db_doc_path: str) -> Optional[str]:
        """根据数据库文档路径查找对应的 DDL 文件"""
        # 从文档路径提取表名
        # 例如：modules/order/storage/db-t_order.md -> t_order

        doc_path = Path(db_doc_path)
        filename = doc_path.stem  # db-t_order

        if filename.startswith('db-'):
            table_name = filename[3:]  # t_order
        else:
            table_name = filename

        # 搜索可能的 DDL 文件路径
        possible_paths = [
            f"migrations/*_{table_name}.sql",
            f"sql/{table_name}.sql",
            f"database/migrations/*_{table_name}.sql",
        ]

        for pattern in possible_paths:
            matches = list(Path('.').glob(pattern))
            if matches:
                return str(matches[0])

        return None



def print_issues(issues: Dict[str, List[LintIssue]], strict: bool = False):
    """
    打印检查结果

    Args:
        issues: {文档路径: 问题列表}
        strict: 严格模式（有错误时返回非 0 退出码）
    """
    total_errors = 0
    total_warnings = 0

    for doc_path, doc_issues in issues.items():
        print(f"\n{doc_path}:")
        for issue in doc_issues:
            print(f"  {issue.severity.value} {issue.message}")
            if issue.severity == Severity.ERROR:
                total_errors += 1
            elif issue.severity == Severity.WARNING:
                total_warnings += 1

    print(f"\n{'='*60}")
    print(f"总计: {total_errors} 个错误, {total_warnings} 个警告")

    if strict and total_errors > 0:
        exit(1)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python -m tools.knowledge_base.doc_linter check --doc <doc_path>")
        print("  python -m tools.knowledge_base.doc_linter check-module --module <module_name>")
        print("  python -m tools.knowledge_base.doc_linter check-all [--strict]")
        sys.exit(1)

    command = sys.argv[1]
    linter = DocLinter()

    if command == "check" and len(sys.argv) >= 4 and sys.argv[2] == "--doc":
        doc_path = sys.argv[3]
        issues = linter.check_document(doc_path)
        print_issues({doc_path: issues} if issues else {})

    elif command == "check-module" and len(sys.argv) >= 4 and sys.argv[2] == "--module":
        module_name = sys.argv[3]
        issues = linter.check_module(module_name)
        print_issues(issues)

    elif command == "check-all":
        strict = "--strict" in sys.argv
        issues = linter.check_all()
        print_issues(issues, strict=strict)

    else:
        print("无效的命令")
        sys.exit(1)

