"""scaffold 包：从代码反向生成模块文档骨架"""

from .scanner import CodeScanner, ScanResult, ScannedRedisKey
from .generator import ScaffoldGenerator
from .detector import SubprojectDetector, DetectedSubproject

__all__ = [
    "CodeScanner", "ScanResult", "ScannedRedisKey", "ScaffoldGenerator",
    "SubprojectDetector", "DetectedSubproject",
]
