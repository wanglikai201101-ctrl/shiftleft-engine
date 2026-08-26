"""知识图谱：从模块文档中提取节点和边，构建业务追溯图谱。

图谱不是额外维护的东西——它是规范化文档的自然产物。
每篇文档按 engineering-doc-* skill 规范写的关联声明，就是图谱的 edges。

使用方法：
    from packages.core.graph import GraphBuilder, GraphStore

    builder = GraphBuilder(modules_dir="modules")
    graph = builder.build()
    store = GraphStore("graph")
    store.save(graph)
"""

from .builder import GraphBuilder
from .store import GraphStore, Graph

__all__ = ["GraphBuilder", "GraphStore", "Graph"]
