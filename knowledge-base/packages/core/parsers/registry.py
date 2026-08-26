"""解析器注册表：按文件扩展名自动选择解析器"""

from pathlib import Path
from typing import Dict, Type
from .base import BaseParser
from .python_parser import PythonApiParser
from .ddl_parser import DDLParser
from .vue_parser import VueParser


class ParserRegistry:
    """解析器注册表"""

    _parsers: Dict[str, Type[BaseParser]] = {}

    @classmethod
    def register(cls, extensions: list, parser_class: Type[BaseParser]):
        for ext in extensions:
            cls._parsers[ext] = parser_class

    @classmethod
    def get_parser(cls, file_path: str) -> BaseParser:
        ext = Path(file_path).suffix.lower()
        parser_class = cls._parsers.get(ext)
        if not parser_class:
            raise ValueError(f"不支持的文件类型: {ext}（支持: {list(cls._parsers.keys())}）")
        return parser_class()

    @classmethod
    def supported_extensions(cls) -> list:
        return list(cls._parsers.keys())


# 注册内置解析器
ParserRegistry.register([".py"], PythonApiParser)
ParserRegistry.register([".sql"], DDLParser)
ParserRegistry.register([".vue"], VueParser)
