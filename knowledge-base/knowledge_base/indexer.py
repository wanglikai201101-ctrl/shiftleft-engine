"""索引生成器：生成 docs-index.json"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from .scanner import DocumentScanner
from .parser import DocumentParser


class DocumentIndexer:
    """文档索引生成器"""
    
    def __init__(self, base_dir: str = "knowledge-base"):
        """
        初始化索引生成器
        
        Args:
            base_dir: 知识库根目录，默认为 "knowledge-base"
        """
        self.scanner = DocumentScanner(base_dir)
        self.parser = DocumentParser()
        self.base_dir = Path(base_dir)
    
    def generate_index(self, output_path: str = "docs-index.json") -> Dict:
        """
        生成索引文件
        
        Args:
            output_path: 输出文件路径，默认为 "docs-index.json"
            
        Returns:
            索引字典
        """
        # 1. 扫描所有文档
        md_files = self.scanner.scan()
        print(f"扫描到 {len(md_files)} 个文档")
        
        # 2. 解析每个文档
        documents = {}
        for file_path in md_files:
            try:
                relative_path = str(file_path.relative_to(self.base_dir))
                doc_type = self.scanner.get_doc_type(file_path)
                doc_info = self.parser.parse(file_path)
                
                # 如果是存储文档，添加存储类型
                if doc_type == "storage":
                    doc_info["storage_type"] = self.scanner.get_storage_type(file_path)
                
                # 如果是模块文档，提取文档索引
                if doc_type == "module":
                    content = file_path.read_text(encoding="utf-8")
                    module_index = self.parser.extract_module_index(content)
                    doc_info.update(module_index)
                
                documents[relative_path] = {
                    "type": doc_type,
                    **doc_info
                }
                
                print(f"  解析: {relative_path} ({doc_type})")
            except Exception as e:
                print(f"  警告：解析失败 {file_path}: {e}")
        
        # 3. 生成索引
        index = {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "total_documents": len(documents),
            "documents": documents
        }
        
        # 4. 保存到文件
        output_file = Path(output_path)
        output_file.write_text(
            json.dumps(index, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        
        print(f"\n索引生成完成: {output_path}")
        print(f"  总文档数: {len(documents)}")
        print(f"  需求文档: {sum(1 for d in documents.values() if d['type'] == 'requirement')}")
        print(f"  接口文档: {sum(1 for d in documents.values() if d['type'] == 'api')}")
        print(f"  存储文档: {sum(1 for d in documents.values() if d['type'] == 'storage')}")
        print(f"  页面文档: {sum(1 for d in documents.values() if d['type'] == 'page')}")
        print(f"  任务文档: {sum(1 for d in documents.values() if d['type'] == 'job')}")
        print(f"  配置文档: {sum(1 for d in documents.values() if d['type'] == 'config')}")
        print(f"  模块文档: {sum(1 for d in documents.values() if d['type'] == 'module')}")
        return index
    
    def generate_dependency_graph(self, index: Dict, output_path: str = "api-dependencies.md"):
        """
        生成接口依赖图（Markdown 格式）
        
        Args:
            index: 文档索引字典
            output_path: 输出文件路径，默认为 "api-dependencies.md"
        """
        lines = ["# 接口依赖图\n"]
        
        api_count = 0
        for doc_path, doc_info in sorted(index["documents"].items()):
            if doc_info["type"] != "api":
                continue
            
            api_count += 1
            lines.append(f"## {doc_info['title']}\n")
            
            # 上游依赖
            lines.append("### 上游依赖\n")
            if doc_info.get("related_requirements"):
                for req in doc_info["related_requirements"]:
                    req_title = index["documents"].get(req, {}).get("title", req)
                    lines.append(f"- [{req_title}]({req})")
            else:
                lines.append("- 无（用户直接调用）")
            lines.append("")
            
            # 下游依赖
            lines.append("### 下游依赖\n")
            has_downstream = False
            
            if doc_info.get("related_storage"):
                lines.append("- **存储**：")
                for storage in doc_info["related_storage"]:
                    storage_title = index["documents"].get(storage, {}).get("title", storage)
                    lines.append(f"  - [{storage_title}]({storage})")
                has_downstream = True
            
            if doc_info.get("related_configs"):
                lines.append("- **配置**：")
                for config in doc_info["related_configs"]:
                    config_title = index["documents"].get(config, {}).get("title", config)
                    lines.append(f"  - [{config_title}]({config})")
                has_downstream = True
            
            if not has_downstream:
                lines.append("- 无")
            lines.append("")
            
            # 被调用方
            lines.append("### 被调用方\n")
            if doc_info.get("related_pages"):
                for page in doc_info["related_pages"]:
                    page_title = index["documents"].get(page, {}).get("title", page)
                    lines.append(f"- [{page_title}]({page})")
            else:
                lines.append("- 无")
            lines.append("\n---\n")
        
        Path(output_path).write_text("\n".join(lines), encoding="utf-8")
        print(f"\n接口依赖图生成完成: {output_path}")
        print(f"  接口数量: {api_count}")
