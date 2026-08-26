"""子项目自动发现器：从根目录按标志文件识别独立子项目。

使用方法：
    from packages.core.scaffold.detector import SubprojectDetector
    detector = SubprojectDetector("<project-root>")
    subprojects = detector.detect()
    # subprojects = [DetectedSubproject(name="frontend", path=..., type="node", framework="next"), ...]
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class DetectedSubproject:
    """发现的子项目"""
    name: str
    path: Path
    type: str  # "node" | "python" | "java" | "go" | "rust"
    framework: str = ""  # "next" | "vue" | "react" | "express" | "fastapi" | "django" | "flask" | ""
    description: str = ""


# 标志文件 → 项目类型
_MARKER_FILES = {
    "package.json": "node",
    "pyproject.toml": "python",
    "setup.py": "python",
    "requirements.txt": "python",
    "pom.xml": "java",
    "build.gradle": "java",
    "go.mod": "go",
    "Cargo.toml": "rust",
}

# 需要跳过的目录名
_SKIP_DIRS = {
    "node_modules", ".venv", "__pycache__", ".git",
    "dist", "build", ".output", ".next", "target",
    "venv", "env", ".env", "backups", "temp", "template",
}


class SubprojectDetector:
    """从根目录自动发现子项目"""

    def __init__(self, root_dir: str, max_depth: int = 2):
        self.root_dir = Path(root_dir)
        self.max_depth = max_depth

    def detect(self) -> List[DetectedSubproject]:
        """扫描根目录，返回发现的子项目列表"""
        if not self.root_dir.exists():
            return []

        subprojects: List[DetectedSubproject] = []
        seen_paths: set = set()

        self._scan_dir(self.root_dir, depth=0, subprojects=subprojects, seen_paths=seen_paths)

        return subprojects

    def _scan_dir(self, dir_path: Path, depth: int,
                  subprojects: List[DetectedSubproject], seen_paths: set):
        """递归扫描目录寻找子项目标志文件"""
        if depth > self.max_depth:
            return

        if dir_path.name in _SKIP_DIRS:
            return

        found_marker = False
        for marker_file, project_type in _MARKER_FILES.items():
            marker_path = dir_path / marker_file
            if marker_path.exists() and dir_path != self.root_dir:
                abs_path = dir_path.resolve()
                if abs_path not in seen_paths:
                    seen_paths.add(abs_path)
                    subproject = self._build_subproject(dir_path, project_type, marker_path)
                    if subproject:
                        subprojects.append(subproject)
                found_marker = True
                break

        if not found_marker or dir_path == self.root_dir:
            try:
                for child in sorted(dir_path.iterdir()):
                    if child.is_dir() and child.name not in _SKIP_DIRS:
                        self._scan_dir(child, depth + 1, subprojects, seen_paths)
            except PermissionError:
                pass

    def _build_subproject(self, dir_path: Path, project_type: str,
                          marker_path: Path) -> Optional[DetectedSubproject]:
        """构建子项目信息"""
        name = dir_path.name
        framework = ""
        description = ""

        if project_type == "node":
            framework, description = self._detect_node_framework(marker_path)
        elif project_type == "python":
            framework = self._detect_python_framework(dir_path)

        return DetectedSubproject(
            name=name,
            path=dir_path,
            type=project_type,
            framework=framework,
            description=description,
        )

    def _detect_node_framework(self, package_json_path: Path) -> tuple:
        """从 package.json 检测 Node.js 框架"""
        try:
            content = json.loads(package_json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return "", ""

        description = content.get("description", "")
        deps = {}
        deps.update(content.get("dependencies", {}))
        deps.update(content.get("devDependencies", {}))

        scripts = content.get("scripts", {})
        scripts_str = " ".join(scripts.values()).lower()

        if "next" in deps or "next dev" in scripts_str or "next build" in scripts_str:
            return "next", description
        if "nuxt" in deps or "nuxt" in scripts_str:
            return "nuxt", description
        if "vue" in deps:
            return "vue", description
        if "react" in deps:
            return "react", description
        if "express" in deps:
            return "express", description
        if "@nestjs/core" in deps:
            return "nest", description

        return "", description

    def _detect_python_framework(self, dir_path: Path) -> str:
        """检测 Python 框架"""
        indicators = {
            "fastapi": ["fastapi"],
            "django": ["django", "manage.py"],
            "flask": ["flask"],
        }

        req_files = ["requirements.txt", "pyproject.toml", "setup.py"]
        combined_content = ""
        for req_file in req_files:
            req_path = dir_path / req_file
            if req_path.exists():
                try:
                    combined_content += req_path.read_text(encoding="utf-8").lower()
                except OSError:
                    pass

        if (dir_path / "manage.py").exists():
            return "django"

        for framework, keywords in indicators.items():
            for keyword in keywords:
                if keyword in combined_content:
                    return framework

        return ""
