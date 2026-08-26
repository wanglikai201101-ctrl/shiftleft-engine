"""解析器抽象基类"""

from abc import ABC, abstractmethod
from typing import Optional
from ..models.doc_types import ExtractedApiInfo


class BaseParser(ABC):
    """代码解析器基类，所有语言解析器继承此类"""

    @abstractmethod
    def extract_api_info(self, code: str, function_name: str) -> Optional[ExtractedApiInfo]:
        """
        从代码中提取接口信息

        Args:
            code: 源代码字符串
            function_name: 函数/方法名

        Returns:
            提取的接口信息，未找到时返回 None
        """
        ...
