# t_charge_item — 订单收费项

## 基本信息

| 字段 | 值 |
|------|-----|
| 存储类型 | 关系型数据库 (MySQL) |
| 模块 | logistics-order |
| 负责人 | 后端开发 |
| 需求来源 | REQ-LO-001, REQ-LO-004 |
| 版本 | v1.0 |

## 字段定义

| 字段 | 类型 | 索引 | 写入来源 | 读取去向 | 业务规则 | 说明 |
|------|------|------|---------|---------|---------|------|
| charge_item_id | varchar(32) | PK | POST /orders | GET /orders/{id}, POST /confirm-charges | UUID | 主键 |
| order_id | varchar(32) | INDEX | POST /orders | GET /orders/{id}, POST /confirm-charges | 外键 → t_order.order_id | 所属订单 |
| service_item_id | varchar(32) | INDEX | POST /orders | GET /orders/{id} | 外键 → t_service_item.service_item_id | 所属服务项 |
| charge_name | varchar(100) | — | POST /orders(从费率表) | order-detail 页面 | 如"国际运费"、"报关费" | 费用名称 |
| unit_price | decimal(10,4) | — | POST /orders(从费率表) | order-detail 页面 | 从 t_service_catalog.unit_price 查询 | 单价 |
| quantity | decimal(10,2) | — | POST /orders(=服务项数量) | order-detail 页面 | = 对应 service_item.quantity | 计费数量 |
| amount | decimal(12,2) | — | POST /orders(计算) | order-detail, POST /invoices | = ROUND(unit_price × quantity, 2) 四舍五入 | 金额 |
| adjusted | boolean | — | POST /confirm-charges | order-detail | 默认 false；运营调整后 true | 是否已调整 |
| adjusted_amount | decimal(12,2) | — | POST /confirm-charges | order-detail, POST /invoices | 运营手动调整的金额；未调整时 = amount | 调整后金额 |

## 关联表

| 表 | 关系 | 关联字段 | 数据流向 |
|-----|------|---------|---------|
| t_order | 多对一 | order_id | charge_item → order（汇总 total_amount） |
| t_service_item | 多对一 | service_item_id | service_item → charge_item |

## 多入口操作对比

### amount 的多入口对比

| 入口 | 操作 | 业务规则 | 代码位置 | 前置条件 |
|------|------|---------|---------|---------|
| POST /orders | INSERT amount=ROUND(unit_price×quantity, 2) | 创建时自动计算 | `OrderService#createOrder` | — |
| POST /confirm-charges | UPDATE adjusted_amount={手动值} | 运营可调整金额 | `OrderService#confirmCharges` | order.status='delivered' |

## 变更记录

| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 关联需求/缺陷 |
|------|------|--------|--------|--------|-------------|
| v1.0 | 2025-04-17 | 示范 | 无（新建） | 创建收费项表文档 | REQ-LO-001 |
