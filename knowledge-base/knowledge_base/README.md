# DocGuardian - 文档填写助手

## 简介

DocGuardian 是一个智能文档填写助手（早期私有化工程），帮助研发快速生成知识库文档。

**核心功能**：
- 自动从代码中提取字段（预填充 80%）
- 研发只需补充业务逻辑（20%）
- 支持命令行和 AI 调用两种方式

**预期效果**：
- 文档填写时间：10 分钟 → 2 分钟（降低 80%）
- 文档填写率：0% → 50%+（一期目标）

---

## 使用方式

### 方式 1：命令行（研发直接调用）

```bash
# 生成接口文档
python -m tools.knowledge_base.doc_guardian api \
    --file sevice/api/order.py \
    --function create_order

# 交互式填写
✅ 检测到接口：POST /orders
✅ 已预填充以下字段：
   - 接口路径：/orders
   - 请求方法：POST
   - 请求参数：order_no(string), amount(number)

请补充以下信息：
1. 模块名（如 order）: order
2. 业务规则（多条用分号分隔，直接回车跳过）: 
> 订单金额必须 >0; 订单明细不能为空
3. 异常场景（多条用分号分隔，直接回车跳过）: 
> 库存不足返回 400; 用户余额不足返回 402
4. 关联数据库表（多个用逗号分隔，直接回车跳过）: 
> t_order, t_order_item
5. 关联前端页面（多个用逗号分隔，直接回车跳过）: 
> OrderCreate.vue

✅ 文档已生成：knowledge-base/modules/order/apis/POST-orders.md
```

### 方式 2：AI 调用（通过 Vibe Coding）

```
研发：帮我生成 create_order 接口的文档

AI：好的，我检测到接口 POST /orders，已预填充以下字段：
   - 接口路径：/orders
   - 请求方法：POST
   - 请求参数：order_no(string), amount(number)

请补充：
1. 模块名
2. 业务规则
3. 异常场景

研发：模块名是 order，业务规则是订单金额必须 >0，异常场景是库存不足返回 400

AI：✅ 文档已生成：knowledge-base/modules/order/apis/POST-orders.md
```

---

## 生成的文档示例

```markdown
# POST /orders

## 接口描述
创建订单

## 请求参数
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| order_no | string | 是 | 订单号 |
| amount | number | 是 | 订单金额 |
| items | array | 是 | 订单明细 |

## 业务规则
- 订单金额必须 >0
- 订单明细不能为空

## 异常场景
- 库存不足 → 返回 400
- 用户余额不足 → 返回 402

## 关联资源
**数据库表**：
- [[file:../database/t_order.md]]
- [[file:../database/t_order_item.md]]

**前端页面**：
- [[file:../page/OrderCreate.md]]
```

---

## 技术架构

```
tools/knowledge_base/
├── doc_guardian.py          # 核心工具类
│   ├── FieldExtractor       # 字段提取器（从代码中提取字段）
│   ├── DocTemplateGenerator # 文档生成器（生成 Markdown 文档）
│   └── DocGuardian          # 主类（协调整个流程）
├── doc_guardian_mcp.py      # MCP 工具封装（供 AI 调用）
└── README.md                # 本文档

tests/
└── test_doc_guardian.py     # 单元测试
```

---

## 开发计划

### ✅ 一期（已完成）

- [x] FieldExtractor：从代码中提取接口字段
- [x] DocTemplateGenerator：生成 Markdown 文档
- [x] DocGuardian：完整流程（命令行 + MCP 工具）
- [x] 单元测试：覆盖核心功能

### 🚧 二期（计划中）

- [ ] 支持代码注释生成文档（`@doc-*` 标签）
- [ ] 支持数据库文档生成（从 SQL 文件提取）
- [ ] 支持页面文档生成（从 Vue 文件提取）

### 🚧 三期（计划中）

- [ ] Git Hook 强制校验（提交代码时检查文档）
- [ ] CI/CD 集成（检查文档与代码一致性）
- [ ] 文档覆盖率报告

---

## 常见问题

### Q1：工具支持哪些文档类型？

**A1**：一期支持接口文档（api），二期将支持数据库文档（database）、页面文档（page）、定时任务文档（job）、配置文档（config）。

### Q2：如果代码改了，文档会自动更新吗？

**A2**：不会。研发需要手动重新运行工具更新文档。二期会支持 Git Hook 自动检测代码变更并提示更新文档。

### Q3：工具能提取 Pydantic 模型的字段吗？

**A3**：一期暂不支持，只能提取函数参数。二期会支持递归解析 Pydantic 模型。

### Q4：如果研发跳过所有补充信息会怎样？

**A4**：工具会生成最小化的文档，业务规则、异常场景等字段会显示"待补充"。

---

## 贡献指南

欢迎提交 Issue 和 PR！

**开发环境**：
```bash
# 安装依赖
pip install pytest

# 运行测试
pytest tests/test_doc_guardian.py -v

# 运行工具
python -m tools.knowledge_base.doc_guardian api --file xxx.py --function xxx
```

---

## 许可证

内部工具，仅供示例团队使用。

---

## 联系方式

- 负责人：示例团队
- 创建时间：2025-04-20
