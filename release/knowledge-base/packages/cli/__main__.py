"""
CLI 入口：python -m packages.cli

用法（新命令 — 需求驱动工作流）：
  python -m packages.cli decompose --req modules/user-auth/requirements/REQ-UA-001.md
  python -m packages.cli fill --doc modules/order/apis/POST-orders.md --code service/api/order.py --function create_order
  python -m packages.cli check --all [--strict]
  python -m packages.cli check --module logistics-order
  python -m packages.cli check --doc modules/order/apis/POST-orders.md
  python -m packages.cli trace --id REQ-LO-001
  python -m packages.cli index --output docs-index.json

旧命令（保留，输出弃用警告）：
  python -m packages.cli generate api --file x.py --function create_order --module order
  python -m packages.cli lint --module logistics-order
  python -m packages.cli lint --all [--strict]
  python -m packages.cli test api --doc path/to/api.md --output tests/test_api.py
"""

import sys
import argparse
from pathlib import Path


# ── New commands (requirement-driven workflow) ──────────────────────


def cmd_decompose(args):
    """需求分解：从需求文档生成关联文档骨架"""
    from packages.core.requirement_decomposer.decomposer import RequirementDecomposer

    decomposer = RequirementDecomposer(knowledge_base_path=args.kb_path)
    result = decomposer.decompose(args.req)

    if result.success:
        print(f"✅ {result.message}")
        print(f"   需求编号: {result.requirement_id}")
        print(f"   关联文档: {len(result.associated_docs)} 个")
        if result.generated_skeletons:
            print("   生成的骨架:")
            for skeleton in result.generated_skeletons:
                print(f"     - {skeleton}")
        if result.warnings:
            print("   ⚠️  警告:")
            for warning in result.warnings:
                print(f"     - {warning}")
    else:
        print(f"❌ {result.message}")
        sys.exit(1)


def cmd_fill(args):
    """技术细节填充：从代码提取细节填入文档骨架"""
    from packages.core.detail_filler.filler import DetailFiller

    filler = DetailFiller()
    result = filler.fill(
        skeleton_path=args.doc,
        code_path=args.code,
        function_name=args.function,
    )

    if result.success:
        print(f"✅ {result.message}")
        if result.filled_fields:
            print("   填充的字段:")
            for field in result.filled_fields:
                print(f"     - {field}")
        if result.conflicts:
            print("   ⚠️  冲突:")
            for conflict in result.conflicts:
                print(f"     - {conflict}")
        if result.preserved_fields:
            print(f"   保留字段: {len(result.preserved_fields)} 个")
    else:
        print(f"❌ {result.message}")
        sys.exit(1)


def cmd_check(args):
    """代码符合性检查：验证代码是否匹配文档"""
    from packages.core.validators.linter import DocLinter

    linter = DocLinter(knowledge_base_path=args.kb_path)

    if args.all:
        report = linter.check_code_conformance()
    elif args.module:
        report = linter.check_code_conformance(module=args.module)
    elif args.doc:
        report = linter.check_code_conformance(doc_path=args.doc)
    else:
        print("❌ 请指定 --all、--module 或 --doc")
        sys.exit(1)

    # 输出结果
    for doc_path, doc_issues in report.issues.items():
        print(f"\n{doc_path}:")
        for issue in doc_issues:
            print(f"  {issue}")

    print(f"\n{'=' * 60}")
    print(f"总计: {report.error_count} 个错误, {report.warning_count} 个警告")

    if report.passed:
        print("✅ 检查通过")
    else:
        print("❌ 检查未通过")

    if args.strict and not report.passed:
        sys.exit(1)


def cmd_trace(args):
    """追溯链查询：从任意标识符查询完整追溯链"""
    from packages.core.indexing.traceability import TraceabilityQuery

    try:
        query = TraceabilityQuery()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print("   提示: 请先运行 'python -m packages.cli index' 生成索引")
        sys.exit(1)

    result = query.trace(args.id)

    print(f"追溯链查询: {result.source}")
    print(f"{'=' * 60}")

    if result.requirement_sources:
        print(f"  需求来源: {', '.join(result.requirement_sources)}")
    if result.test_points:
        print(f"  测试点: {', '.join(result.test_points)}")
    if result.downstream_apis:
        print(f"  下游接口: {', '.join(result.downstream_apis)}")
    if result.downstream_storage:
        print(f"  下游存储: {', '.join(result.downstream_storage)}")
    if result.downstream_pages:
        print(f"  下游页面: {', '.join(result.downstream_pages)}")
    if result.downstream_jobs:
        print(f"  下游任务: {', '.join(result.downstream_jobs)}")
    if result.broken_links:
        print(f"  ⚠️  断裂链接: {', '.join(result.broken_links)}")

    if not any([
        result.requirement_sources, result.test_points,
        result.downstream_apis, result.downstream_storage,
        result.downstream_pages, result.downstream_jobs,
    ]):
        print("  （未找到追溯信息）")


def cmd_index(args):
    """生成文档索引"""
    from packages.core.indexing.indexer import DocumentIndexer

    # --output 的父目录可能不存在；先确保存在，避免写索引时 FileNotFoundError
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    indexer = DocumentIndexer(base_dir=args.kb_path)
    index = indexer.generate_index(output_path=args.output)
    print(f"✅ 索引生成完成: {args.output}（{index['total_documents']} 个文档）")


def cmd_graph(args):
    """知识图谱操作"""
    from packages.core.graph import Graph, GraphBuilder, GraphStore

    if args.action == "build":
        builder = GraphBuilder(modules_dir=args.kb_path)
        graph = builder.build(merge=args.merge, graph_output_dir=args.output)
        store = GraphStore(output_dir=args.output)
        output_path = store.save(graph)
        index_path = store.save_adjacency_index(graph)
        search_index_path = store.save_search_index(graph)

        # Generate HTML visualization
        from packages.core.graph.visualize import generate_html
        html_path = generate_html(graph, output_path=f"{args.output}/graph.html")

        stats = graph.stats
        print(f"  Graph built: {output_path}")
        print(f"   Adjacency index: {index_path}")
        print(f"   Search index: {search_index_path}")
        print(f"   Visualization: {html_path}")
        print(f"   Nodes: {stats['total_nodes']} | Edges: {stats['total_edges']} | Modules: {stats['modules']}")
        print(f"   Node types: {stats['node_types']}")
        print(f"   Edge relations: {stats['edge_relations']}")

        # Orphan report
        if graph.orphan_report:
            print(f"\n  [WARN] orphan nodes: {len(graph.orphan_report)}")
            for o in graph.orphan_report:
                print(f"    [{o['type']}] {o['node_id']}")
                print(f"          doc: {o['doc_path']}")
            print("  -> check these docs for missing cross-references")
        else:
            print(f"\n  [OK] zero orphans")

    elif args.action == "view":
        import webbrowser
        html_path = Path(args.output) / "graph.html"
        if not html_path.exists():
            print("❌ graph.html 不存在，请先运行 graph build")
            return
        webbrowser.open(str(html_path.resolve()))
        print(f"✅ 已在浏览器中打开: {html_path}")

    elif args.action == "impact":
        if not args.node:
            print("❌ 请指定 --node 参数")
            return
        store = GraphStore(output_dir=args.output)
        graph = store.load()
        if not graph:
            print("❌ 图谱不存在，请先运行 graph build")
            return
        impacted = graph.impact(args.node)
        if impacted:
            print(f"影响分析: {args.node} → {len(impacted)} 个关联节点")
            for nid in impacted:
                node = graph.get_node(nid)
                label = node.label if node else nid
                ntype = node.type if node else "?"
                print(f"  [{ntype}] {label}")
        else:
            print(f"未找到 {args.node} 的关联节点（确认节点 ID 正确）")

    elif args.action == "coverage":
        if not args.node:
            print("❌ 请指定 --node 参数（需求 ID）")
            return
        store = GraphStore(output_dir=args.output)
        graph = store.load()
        if not graph:
            print("❌ 图谱不存在，请先运行 graph build")
            return
        cov = graph.coverage(args.node)
        print(f"覆盖检查: {cov['requirement_id']}")
        print(f"  已覆盖类型: {cov['covered_types']}")
        print(f"  已覆盖节点: {cov['covered_nodes']}")
        if cov['missing_types']:
            print(f"  ⚠️  缺失类型: {cov['missing_types']}")
        else:
            print("  ✅ 全部覆盖")

    elif args.action == "orphans":
        store = GraphStore(output_dir=args.output)
        graph = store.load()
        if not graph:
            print("❌ 图谱不存在，请先运行 graph build")
            return
        orphan_nodes = graph.orphans()
        if orphan_nodes:
            print(f"孤立节点: {len(orphan_nodes)} 个（无关联）")
            for n in orphan_nodes:
                print(f"  [{n.type}] {n.id} — {n.label}")
        else:
            print("✅ 无孤立节点")

    elif args.action == "repair-orphans":
        from packages.core.graph.orphan_repair import OrphanRepairer

        store = GraphStore(output_dir=args.output)
        graph = store.load()
        if not graph:
            print("graph not found, run graph build first")
            return
        repairer = OrphanRepairer(modules_dir=args.kb_path, graph=graph)
        report = repairer.repair()

        if report["repaired"]:
            print(f"[FIXED] {len(report['repaired'])} orphans repaired:")
            for item in report["repaired"]:
                print(f"  [{item['type']}] {item['node_id']}")
                for edge in item["edges_added"]:
                    print(f"        + {edge['relation']} -> {edge['target']}")
            # Save updated graph
            store.save(graph)
            store.save_adjacency_index(graph)
            print(f"\n  graph.json updated ({graph.stats['total_edges']} edges)")
        else:
            print("[OK] no repairable orphans found")

        if report["unresolved"]:
            print(f"\n[UNRESOLVED] {len(report['unresolved'])} orphans need manual fix:")
            for item in report["unresolved"]:
                print(f"  [{item['type']}] {item['node_id']}")
                print(f"        reason: {item['reason']}")
                print(f"        doc: {item['doc_path']}")

    elif args.action == "query":
        if not args.node and not args.search:
            print("❌ 请指定 --node 参数（精确节点 ID）或 --search 参数（模糊搜索）")
            return
        store = GraphStore(output_dir=args.output)
        graph = store.load()
        if not graph:
            print("❌ 图谱不存在，请先运行 graph build")
            return

        # 模糊搜索模式：先找节点，再对每个匹配节点执行查询
        if args.search:
            types_filter = args.types.split(",") if args.types else None
            synonyms = Graph.load_synonyms()
            matched_nodes = graph.search_nodes(args.search, node_types=types_filter, synonyms=synonyms)
            if not matched_nodes:
                print(f"未找到包含 \"{args.search}\" 的节点")
                return

            if args.hops == 0:
                # hops=0: 只展示搜索结果本身，不查关联
                print(f"搜索: \"{args.search}\" (共 {len(matched_nodes)} 个匹配)")
                print(f"{'─' * 60}")
                for n in matched_nodes:
                    print(f"  [{n.type}] {n.label} (id={n.id})")
                print(f"{'─' * 60}")
                return

            # hops>0: 对每个匹配节点展开查询
            print(f"搜索: \"{args.search}\" → {len(matched_nodes)} 个匹配节点，展开 {args.hops} 跳关联")
            print(f"{'═' * 60}")
            relations_filter = args.relations.split(",") if args.relations else None
            for node in matched_nodes[:5]:  # 最多展开前 5 个匹配
                results = graph.query(
                    start=node.id,
                    max_hops=args.hops,
                    relations=relations_filter,
                    node_types=types_filter,
                    direction=args.direction,
                    min_confidence=args.confidence,
                    budget=args.budget,
                )
                print(f"\n  [{node.type}] {node.label}")
                print(f"  {'─' * 50}")
                if results:
                    for r in results:
                        conf_tag = f" [{r['confidence']}]" if r.get('confidence') != 'EXTRACTED' else ""
                        print(f"    → [{r['node_type']}] {r['label']} (hop={r['hop']}, via={r['relation']}{conf_tag})")
                else:
                    print(f"    (无关联节点)")
            if len(matched_nodes) > 5:
                print(f"\n  ... 还有 {len(matched_nodes) - 5} 个匹配未展开")
            print(f"\n{'═' * 60}")
            return

        # 精确查询模式（原逻辑）
        relations_filter = args.relations.split(",") if args.relations else None
        types_filter = args.types.split(",") if args.types else None
        results = graph.query(
            start=args.node,
            max_hops=args.hops,
            relations=relations_filter,
            node_types=types_filter,
            direction=args.direction,
            min_confidence=args.confidence,
            budget=args.budget,
        )
        if results:
            print(f"查询: {args.node} (hops={args.hops}, direction={args.direction}, confidence>={args.confidence}, budget={args.budget or 'unlimited'})")
            print(f"{'─' * 60}")
            for r in results:
                conf_tag = f" [{r['confidence']}]" if r.get('confidence') != 'EXTRACTED' else ""
                print(f"  [{r['node_type']}] {r['label']} (hop={r['hop']}, via={r['relation']}{conf_tag})")
            print(f"{'─' * 60}")
            print(f"共 {len(results)} 个结果")
        else:
            print(f"未找到 {args.node} 的关联节点（确认节点 ID 和过滤条件）")

    elif args.action == "backfill-links":
        store = GraphStore(output_dir=args.output)
        graph = store.load()
        if not graph:
            print("❌ 图谱不存在，请先运行 graph build")
            return

        import os
        kb_path = args.kb_path
        # Find module dir (first subdir of kb_path that has apis/)
        module_dir = None
        for d in Path(kb_path).iterdir():
            if d.is_dir() and (d / "apis").exists():
                module_dir = d
                break
        if not module_dir:
            print(f"❌ 未找到模块目录（含 apis/ 子目录）: {kb_path}")
            return

        module_name = module_dir.name
        stats = {"api_req_added": 0, "storage_req_added": 0, "page_req_added": 0, "req_links_fixed": 0}

        # Build reverse index: api_node_id → [req_node_ids]
        api_to_reqs = {}
        for e in graph.edges:
            if e.relation == "implemented_by":
                node = graph.get_node(e.to_id)
                if node and node.type == "api":
                    api_to_reqs.setdefault(e.to_id, []).append(e.from_id)

        # 1. Add ## 需求来源 to API docs
        api_dir = module_dir / "apis"
        if api_dir.exists():
            for f in api_dir.glob("*.md"):
                content = f.read_text(encoding="utf-8", errors="ignore")
                if "## 需求来源" in content:
                    continue
                api_node_id = f"{module_name}:api:{f.stem}"
                req_ids = api_to_reqs.get(api_node_id, [])
                if not req_ids:
                    continue
                # Build section
                lines = ["\n## 需求来源\n", "| 需求 ID | 需求名称 |", "|---------|---------|"]
                for req_id in sorted(set(req_ids)):
                    req_node = graph.get_node(req_id)
                    label = req_node.label if req_node else req_id
                    short_id = req_id.replace(f"{module_name}:", "")
                    lines.append(f"| {short_id} | {label} |")
                # Insert after ## 基本信息 section, before ## 请求参数
                insert_point = content.find("## 请求参数")
                if insert_point == -1:
                    insert_point = content.find("## 响应结构")
                if insert_point == -1:
                    content += "\n".join(lines) + "\n"
                else:
                    content = content[:insert_point] + "\n".join(lines) + "\n\n" + content[insert_point:]
                f.write_text(content, encoding="utf-8")
                stats["api_req_added"] += 1

        # 2. Add ## 关联需求 to storage docs
        # Build: storage_node_id → [req_ids] (via writes_to reverse + implemented_by)
        storage_to_reqs = {}
        for e in graph.edges:
            if e.relation in ("writes_to", "reads_from"):
                api_id = e.from_id
                storage_id = e.to_id
                for req_id in api_to_reqs.get(api_id, []):
                    storage_to_reqs.setdefault(storage_id, set()).add((req_id, api_id))

        storage_dir = module_dir / "storage"
        if storage_dir.exists():
            for f in storage_dir.glob("*.md"):
                content = f.read_text(encoding="utf-8", errors="ignore")
                if "## 关联需求" in content:
                    continue
                storage_node_id = f"{module_name}:table:{f.stem}"
                req_pairs = storage_to_reqs.get(storage_node_id, set())
                if not req_pairs:
                    continue
                # Group by req
                from collections import defaultdict
                req_apis = defaultdict(list)
                for req_id, api_id in req_pairs:
                    api_node = graph.get_node(api_id)
                    api_label = api_node.label if api_node else api_id.split(":")[-1]
                    req_apis[req_id].append(api_label)
                lines = ["\n## 关联需求\n", "| 需求 | 关系 | 说明 |", "|------|------|------|"]
                for req_id in sorted(req_apis.keys()):
                    req_node = graph.get_node(req_id)
                    short_id = req_id.replace(f"{module_name}:", "")
                    label = req_node.label if req_node else short_id
                    apis_str = ", ".join(sorted(set(req_apis[req_id]))[:3])
                    lines.append(f"| {short_id} | 通过 {apis_str} 写入 | {label} |")
                content += "\n".join(lines) + "\n"
                f.write_text(content, encoding="utf-8")
                stats["storage_req_added"] += 1

        # 3. Add ## 关联需求 to page docs
        # Build: page_node_id → [req_ids] (via calls reverse + implemented_by)
        page_to_reqs = {}
        for e in graph.edges:
            if e.relation == "calls":
                page_id = e.from_id
                api_id = e.to_id
                for req_id in api_to_reqs.get(api_id, []):
                    page_to_reqs.setdefault(page_id, set()).add((req_id, api_id))

        pages_dir = module_dir / "pages"
        if pages_dir.exists():
            for f in pages_dir.glob("*.md"):
                content = f.read_text(encoding="utf-8", errors="ignore")
                if "## 关联需求" in content:
                    continue
                page_node_id = f"{module_name}:page:{f.stem}"
                req_pairs = page_to_reqs.get(page_node_id, set())
                if not req_pairs:
                    continue
                from collections import defaultdict
                req_apis = defaultdict(list)
                for req_id, api_id in req_pairs:
                    api_node = graph.get_node(api_id)
                    api_label = api_node.label if api_node else api_id.split(":")[-1]
                    req_apis[req_id].append(api_label)
                lines = ["\n## 关联需求\n", "| 需求 | 触发接口 | 说明 |", "|------|---------|------|"]
                for req_id in sorted(req_apis.keys()):
                    req_node = graph.get_node(req_id)
                    short_id = req_id.replace(f"{module_name}:", "")
                    label = req_node.label if req_node else short_id
                    apis_str = ", ".join(sorted(set(req_apis[req_id]))[:3])
                    lines.append(f"| {short_id} | {apis_str} | {label} |")
                content += "\n".join(lines) + "\n"
                f.write_text(content, encoding="utf-8")
                stats["page_req_added"] += 1

        print(f"✅ 追溯链接回填完成:")
        print(f"   API → REQ (需求来源):  {stats['api_req_added']} 个文档已更新")
        print(f"   Storage → REQ (关联需求): {stats['storage_req_added']} 个文档已更新")
        print(f"   Page → REQ (关联需求):   {stats['page_req_added']} 个文档已更新")

    elif args.action == "stats":
        store = GraphStore(output_dir=args.output)
        graph = store.load()
        if not graph:
            print("❌ 图谱不存在，请先运行 graph build")
            return
        stats = graph.stats
        print("图谱统计:")
        print(f"  节点: {stats['total_nodes']} | 边: {stats['total_edges']} | 模块: {stats['modules']}")
        print(f"  节点类型: {stats['node_types']}")
        print(f"  关系类型: {stats['edge_relations']}")


def cmd_regression(args):
    """变更驱动回归分析（图谱影响分析 + 回归用例识别，不含真实执行）"""
    from packages.core.regression import RegressionRunner, get_git_diff_files

    # Step 1: Get changed files
    if args.files:
        changed_files = args.files
    else:
        changed_files = get_git_diff_files(since=args.since)
        if not changed_files:
            print(f"[!] git diff {args.since} 未检测到变更文件")
            return

    print(f"[1/5] Git diff 分析...")
    print(f"  变更文件: {len(changed_files)} 个")
    for f in changed_files[:10]:
        print(f"    {f}")
    if len(changed_files) > 10:
        print(f"    ... 及 {len(changed_files) - 10} 个更多")

    # Step 2-4: Analyze
    runner = RegressionRunner(
        module=args.module,
        kb_path=args.output,
        graph_dir=args.graph_dir,
    )
    report = runner.run(changed_files, dry_run=args.dry_run)

    # Display results
    print(f"\n[2/5] 映射到图谱节点...")
    if report.mapped_nodes:
        for nid in report.mapped_nodes[:10]:
            print(f"  → {nid}")
    else:
        print("  [!] 未能映射到任何图谱节点")
        return

    print(f"\n[3/5] 影响分析...")
    print(f"  直接受影响: {len(report.mapped_nodes)} 节点")
    print(f"  间接影响: +{len(report.impact_scope)} 节点")
    print(f"  总回归范围: {len(report.mapped_nodes) + len(report.impact_scope)} 节点")

    print(f"\n[4/5] 测试类型决策...")
    if report.test_plan and not report.test_plan.is_empty:
        plan = report.test_plan
        if plan.api_scope:
            print(f"  → API contract tests: {len(plan.api_scope)} APIs")
        if plan.page_scope:
            print(f"  → UI tests: {len(plan.page_scope)} Pages")
        if plan.chains:
            print(f"  → E2E chains: {len(plan.chains)} 条跨层链路")
    else:
        print("  [!] 无法生成测试计划")
        return

    print(f"\n[5/5] 测试选择...")
    if report.skipped_no_tests:
        print(f"  [!] 缺失测试覆盖: {len(report.skipped_no_tests)} 节点")
        for nid in report.skipped_no_tests[:5]:
            print(f"    - {nid}")

    if args.dry_run:
        print(f"\n{'═' * 60}")
        print("REGRESSION PLAN (dry-run, 未执行)")
        print(f"{'═' * 60}")
        print(report.summary())
        print(f"\n使用不带 --dry-run 参数执行测试")
    else:
        print(f"\n{'═' * 60}")
        print("REGRESSION REPORT")
        print(f"{'═' * 60}")
        print(report.summary())
        if report.failed > 0:
            print(f"\n❌ 失败用例:")
            for r in report.executed:
                if not r.passed:
                    print(f"  [{r.test_type}] {r.name}: {r.details}")


def cmd_batch_fill(args):
    """批量填充文档骨架的技术细节"""
    from packages.core.batch import BatchFiller

    filler = BatchFiller(
        modules_dir=args.kb_path,
        source_dir=args.source,
    )
    result = filler.run(module=args.module, workers=args.workers)

    print(f"📡 批量填充完成: {result.summary}")

    filled_count = sum(1 for d in result.details if d["status"] == "filled")
    skipped_count = sum(1 for d in result.details if d["status"] == "skipped")
    failed_count = sum(1 for d in result.details if d["status"] in ("failed", "error"))

    if filled_count:
        print(f"\n✅ 已填充 {filled_count} 个文档:")
        for d in result.details:
            if d["status"] == "filled":
                fields = d.get("fields", [])
                print(f"    + {d['doc']} ({len(fields)} 字段)")

    if skipped_count:
        print(f"\n⏭️  跳过 {skipped_count} 个（无匹配源文件）")

    if failed_count:
        print(f"\n❌ 失败 {failed_count} 个:")
        for d in result.details:
            if d["status"] in ("failed", "error"):
                print(f"    - {d['doc']}: {d.get('reason', 'unknown')}")


def cmd_scaffold(args):
    """从代码反向生成模块文档骨架（支持子项目自动发现+多源目录）"""
    from packages.core.scaffold import CodeScanner, ScaffoldGenerator
    from packages.core.scaffold.detector import SubprojectDetector
    from packages.core.scaffold.scanner import ScanResult

    # args.source is now a list (nargs="+")
    sources = args.source if isinstance(args.source, list) else [args.source]
    auto_detect = getattr(args, "auto_detect", True)

    # Multi-source mode: scan each source into a merged result
    if len(sources) > 1 or not auto_detect:
        merged = ScanResult()
        seen_apis: set = set()
        seen_tables: set = set()
        seen_pages: set = set()
        seen_jobs: set = set()
        for src in sources:
            print(f"📂 扫描: {src}")
            scanner = CodeScanner(src)
            partial = scanner.scan()
            for api in partial.apis:
                key = (api.method, api.path)
                if key not in seen_apis:
                    seen_apis.add(key)
                    merged.apis.append(api)
            for table in partial.tables:
                if table.table_name not in seen_tables:
                    seen_tables.add(table.table_name)
                    merged.tables.append(table)
            for page in partial.pages:
                if page.component_name not in seen_pages:
                    seen_pages.add(page.component_name)
                    merged.pages.append(page)
            for job in partial.jobs:
                if job.job_name not in seen_jobs:
                    seen_jobs.add(job.job_name)
                    merged.jobs.append(job)
            merged.redis_keys.extend(partial.redis_keys)
            merged.errors.extend(partial.errors)

        if merged.total == 0 and not merged.errors:
            print(f"⚠️  未扫描到接口/表/页面/任务")
            return

        print(f"\n📡 合并扫描: {len(merged.apis)} 接口, "
              f"{len(merged.tables)} 表, "
              f"{len(merged.redis_keys)} Redis Key, "
              f"{len(merged.pages)} 页面, "
              f"{len(merged.jobs)} 任务")

        if merged.errors:
            print(f"⚠️  扫描警告: {len(merged.errors)} 个")
            for err in merged.errors[:5]:
                print(f"    - {err}")

        generator = ScaffoldGenerator(
            output_dir=args.output,
            module_name=args.module,
        )
        gen_result = generator.generate(merged)

        if gen_result.generated_files:
            print(f"\n✅ 生成 {len(gen_result.generated_files)} 个文件:")
            for f in gen_result.generated_files[:20]:
                print(f"    + {f}")
            if len(gen_result.generated_files) > 20:
                print(f"    ... 及 {len(gen_result.generated_files) - 20} 个更多")

        if gen_result.skipped_files:
            print(f"\n⏭️  跳过 {len(gen_result.skipped_files)} 个已存在文件")

        if gen_result.errors:
            print(f"\n❌ 错误 {len(gen_result.errors)} 个:")
            for err in gen_result.errors[:5]:
                print(f"    - {err}")
        return

    # Single source with auto-detect
    source = sources[0]
    if auto_detect:
        detector = SubprojectDetector(source)
        subprojects = detector.detect()
    else:
        subprojects = []

    # Single source with auto-detect
    source = sources[0]
    if auto_detect:
        detector = SubprojectDetector(source)
        subprojects = detector.detect()
    else:
        subprojects = []

    if subprojects:
        print(f"🔍 发现 {len(subprojects)} 个子项目:")
        for sp in subprojects:
            fw = f" ({sp.framework})" if sp.framework else ""
            print(f"    [{sp.type}] {sp.name}{fw} — {sp.path}")
        print()

        total_generated = 0
        total_skipped = 0
        total_errors = 0

        for sp in subprojects:
            sub_module = f"{args.module}/{sp.name}"
            print(f"{'─' * 50}")
            print(f"📦 子项目: {sp.name} ({sp.type}/{sp.framework or 'generic'})")

            scanner = CodeScanner(str(sp.path))
            scan_result = scanner.scan()

            if scan_result.total == 0 and not scan_result.errors:
                print(f"    ⚠️  未扫描到接口/表/页面/任务，跳过")
                continue

            print(f"    扫描: {len(scan_result.apis)} 接口, "
                  f"{len(scan_result.tables)} 表, "
                  f"{len(scan_result.redis_keys)} Redis Key, "
                  f"{len(scan_result.pages)} 页面, "
                  f"{len(scan_result.jobs)} 任务")

            generator = ScaffoldGenerator(
                output_dir=args.output,
                module_name=sub_module,
            )
            gen_result = generator.generate(scan_result)

            if gen_result.generated_files:
                print(f"    ✅ 生成 {len(gen_result.generated_files)} 个文件")
                total_generated += len(gen_result.generated_files)

            if gen_result.skipped_files:
                print(f"    ⏭️  跳过 {len(gen_result.skipped_files)} 个已存在")
                total_skipped += len(gen_result.skipped_files)

            if gen_result.errors:
                print(f"    ❌ 错误 {len(gen_result.errors)} 个")
                total_errors += len(gen_result.errors)

        print(f"\n{'═' * 50}")
        print(f"汇总: {len(subprojects)} 子项目 | "
              f"生成 {total_generated} 文件 | "
              f"跳过 {total_skipped} | "
              f"错误 {total_errors}")

    else:
        # 单模块模式（向后兼容）
        scanner = CodeScanner(source)
        scan_result = scanner.scan()

        if scan_result.total == 0 and not scan_result.errors:
            print(f"⚠️  未在 {source} 中扫描到接口/表/页面/任务")
            return

        print(f"📡 扫描完成: {len(scan_result.apis)} 接口, "
              f"{len(scan_result.tables)} 表, "
              f"{len(scan_result.redis_keys)} Redis Key, "
              f"{len(scan_result.pages)} 页面, "
              f"{len(scan_result.jobs)} 任务")

        if scan_result.errors:
            print(f"⚠️  扫描警告: {len(scan_result.errors)} 个")
            for err in scan_result.errors[:5]:
                print(f"    - {err}")

        generator = ScaffoldGenerator(
            output_dir=args.output,
            module_name=args.module,
        )
        gen_result = generator.generate(scan_result)

        if gen_result.generated_files:
            print(f"\n✅ 生成 {len(gen_result.generated_files)} 个文件:")
            for f in gen_result.generated_files:
                print(f"    + {f}")

        if gen_result.skipped_files:
            print(f"\n⏭️  跳过 {len(gen_result.skipped_files)} 个已存在文件")

        if gen_result.errors:
            print(f"\n❌ 错误 {len(gen_result.errors)} 个:")
            for err in gen_result.errors:
                print(f"    - {err}")


# ── Legacy commands (preserved with deprecation warnings) ──────────


def cmd_generate(args):
    """生成文档（已弃用，建议使用 fill 命令）"""
    print(
        "⚠️  警告: 'generate' 命令已弃用，建议使用 'fill' 命令。"
        "\n   示例: python -m packages.cli fill --doc <骨架路径> --code <代码路径>",
        file=sys.stderr,
    )

    from packages.core.generators.api_doc import ApiDocGenerator

    if args.type == "api":
        if not args.function:
            print("❌ api 类型必须指定 --function")
            sys.exit(1)
        gen = ApiDocGenerator(knowledge_base_path=args.kb_path)
        result = gen.generate(
            file_path=args.file,
            function_name=args.function,
            module=args.module or "default",
        )
        if result.success:
            print(f"✅ {result.message}")
        else:
            print(f"❌ {result.message}")
            sys.exit(1)
    else:
        print(f"❌ 暂不支持 {args.type} 类型（开发中）")
        sys.exit(1)


def cmd_lint(args):
    """文档一致性检查（已弃用，建议使用 check 命令）"""
    print(
        "⚠️  警告: 'lint' 命令已弃用，建议使用 'check' 命令。"
        "\n   示例: python -m packages.cli check --all [--strict]",
        file=sys.stderr,
    )

    from packages.core.validators.linter import DocLinter

    linter = DocLinter(knowledge_base_path=args.kb_path)

    if args.all:
        report = linter.check_all()
    elif args.module:
        report = linter.check_module(args.module)
    elif args.doc:
        issues = linter.check_document(args.doc)
        from packages.core.models.results import LintReport
        report = LintReport(issues={args.doc: issues} if issues else {})
    else:
        print("❌ 请指定 --all、--module 或 --doc")
        sys.exit(1)

    # 输出结果
    for doc_path, doc_issues in report.issues.items():
        print(f"\n{doc_path}:")
        for issue in doc_issues:
            print(f"  {issue}")

    print(f"\n{'=' * 60}")
    print(f"总计: {report.error_count} 个错误, {report.warning_count} 个警告")

    if args.strict and not report.passed:
        sys.exit(1)


def cmd_test(args):
    """生成测试骨架"""
    from packages.core.generators.test_skeleton import ApiTestGenerator, DatabaseTestGenerator

    if args.type == "api":
        code = ApiTestGenerator().generate(args.doc)
    elif args.type == "database":
        code = DatabaseTestGenerator().generate(args.doc)
    else:
        print(f"❌ 不支持的测试类型: {args.type}")
        sys.exit(1)

    Path(args.output).write_text(code, encoding="utf-8")
    print(f"✅ 测试文件已生成: {args.output}")


# ── Main entry point ───────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(prog="kb", description="Engineering Knowledge Base CLI")
    parser.add_argument("--kb-path", default="modules", help="知识库路径（默认 modules）")
    sub = parser.add_subparsers(dest="command", required=True)

    # ── New commands ──

    # decompose
    p_decompose = sub.add_parser("decompose", help="需求分解：从需求文档生成关联文档骨架")
    p_decompose.add_argument("--req", required=True, help="需求文档路径")
    p_decompose.set_defaults(func=cmd_decompose)

    # fill
    p_fill = sub.add_parser("fill", help="技术细节填充：从代码提取细节填入文档骨架")
    p_fill.add_argument("--doc", required=True, help="文档骨架路径")
    p_fill.add_argument("--code", required=True, help="代码文件路径")
    p_fill.add_argument("--function", help="函数名（可选）")
    p_fill.set_defaults(func=cmd_fill)

    # check
    p_check = sub.add_parser("check", help="代码符合性检查：验证代码是否匹配文档")
    p_check.add_argument("--all", action="store_true", help="检查所有文档")
    p_check.add_argument("--module", help="检查指定模块")
    p_check.add_argument("--doc", help="检查单个文档")
    p_check.add_argument("--strict", action="store_true", help="严格模式（有错误则退出码 1）")
    p_check.set_defaults(func=cmd_check)

    # trace
    p_trace = sub.add_parser("trace", help="追溯链查询：从任意标识符查询完整追溯链")
    p_trace.add_argument("--id", required=True, help="查询标识符（文档路径、REQ-xxx 或 TP-xxx）")
    p_trace.set_defaults(func=cmd_trace)

    # scaffold
    p_scaffold = sub.add_parser("scaffold", help="从代码反向生成模块文档骨架（支持子项目自动发现）")
    p_scaffold.add_argument("--source", required=True, nargs="+", help="代码目录路径（支持多个，空格分隔）")
    p_scaffold.add_argument("--module", required=True, help="模块名称")
    p_scaffold.add_argument("--output", default="modules", help="文档输出目录（默认 modules）")
    p_scaffold.add_argument("--auto-detect", dest="auto_detect", action="store_true", default=True,
                            help="自动发现子项目（默认开启）")
    p_scaffold.add_argument("--no-auto-detect", dest="auto_detect", action="store_false",
                            help="禁用子项目自动发现，整目录作为单模块扫描")
    p_scaffold.set_defaults(func=cmd_scaffold)

    # batch-fill
    p_batch = sub.add_parser("batch-fill", help="批量填充文档骨架的技术细节（多线程）")
    p_batch.add_argument("--module", required=True, help="模块名称")
    p_batch.add_argument("--source", required=True, help="代码目录路径")
    p_batch.add_argument("--workers", type=int, default=8, help="并行线程数（默认 8）")
    p_batch.set_defaults(func=cmd_batch_fill)

    # graph
    p_graph = sub.add_parser("graph", help="知识图谱操作：构建、查询、影响分析、可视化")
    p_graph.add_argument("action", choices=["build", "view", "impact", "query", "coverage", "orphans", "repair-orphans", "stats", "backfill-links"],
                         help="操作：build/view/impact/query/coverage/orphans/repair-orphans/stats/backfill-links")
    p_graph.add_argument("--node", help="节点 ID（impact/query/coverage 操作需要）")
    p_graph.add_argument("--search", help="模糊搜索词（query 操作，支持中英文，匹配 label 和 id）")
    p_graph.add_argument("--output", default="graph", help="图谱输出目录（默认 graph）")
    p_graph.add_argument("--merge", action="store_true", default=False,
                         help="合并模式：保留旧图中新扫描未产出的节点/边（防止正则解析失败导致节点丢失）")
    p_graph.add_argument("--hops", type=int, default=1, help="查询跳数（默认 1，最大 3）")
    p_graph.add_argument("--relations", help="关系类型过滤，逗号分隔（如 implements,writes_to）")
    p_graph.add_argument("--types", help="节点类型过滤，逗号分隔（如 api,requirement）")
    p_graph.add_argument("--direction", default="both", choices=["out", "in", "both"],
                         help="遍历方向：out/in/both（默认 both）")
    p_graph.add_argument("--confidence", default="AMBIGUOUS", choices=["EXTRACTED", "INFERRED", "AMBIGUOUS"],
                         help="最低置信度过滤（默认 AMBIGUOUS=全部）")
    p_graph.add_argument("--budget", type=int, default=0,
                         help="最大返回结果数（默认 0=不限），防止结果过大")
    p_graph.set_defaults(func=cmd_graph)

    # ── Preserved commands ──

    # index (unchanged)
    p_idx = sub.add_parser("index", help="生成文档索引")
    p_idx.add_argument("--output", default="docs-index.json", help="输出路径")
    p_idx.set_defaults(func=cmd_index)

    # generate (deprecated)
    p_gen = sub.add_parser("generate", help="生成文档（已弃用，建议使用 fill）")
    p_gen.add_argument("type", choices=["api", "storage", "page"], help="文档类型")
    p_gen.add_argument("--file", required=True, help="代码文件路径")
    p_gen.add_argument("--function", help="函数名（api 必填）")
    p_gen.add_argument("--module", help="模块名")
    p_gen.set_defaults(func=cmd_generate)

    # lint (deprecated)
    p_lint = sub.add_parser("lint", help="文档一致性检查（已弃用，建议使用 check）")
    p_lint.add_argument("--all", action="store_true", help="检查所有文档")
    p_lint.add_argument("--module", help="检查指定模块")
    p_lint.add_argument("--doc", help="检查单个文档")
    p_lint.add_argument("--strict", action="store_true", help="严格模式（有错误则退出码 1）")
    p_lint.set_defaults(func=cmd_lint)

    # test
    p_test = sub.add_parser("test", help="生成测试骨架")
    p_test.add_argument("type", choices=["api", "database"], help="测试类型")
    p_test.add_argument("--doc", required=True, help="文档路径")
    p_test.add_argument("--output", required=True, help="输出路径")
    p_test.set_defaults(func=cmd_test)

    # regression
    p_reg = sub.add_parser("regression", help="变更驱动回归分析：git diff → 图谱影响分析 → 用例识别与影响报告")
    p_reg.add_argument("--module", required=True, help="模块名称")
    p_reg.add_argument("--since", default="HEAD", help="Git ref for diff（默认 HEAD = 未提交变更）")
    p_reg.add_argument("--files", nargs="+", help="手动指定变更文件（跳过 git diff）")
    p_reg.add_argument("--type", choices=["api", "e2e", "ui"], help="强制测试类型（跳过自动决策）")
    p_reg.add_argument("--dry-run", dest="dry_run", action="store_true", help="只输出计划，不执行")
    p_reg.add_argument("--output", default="modules", help="KB 文档目录（默认 modules）")
    p_reg.add_argument("--graph-dir", dest="graph_dir", default="graph", help="图谱目录（默认 graph）")
    p_reg.set_defaults(func=cmd_regression)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
