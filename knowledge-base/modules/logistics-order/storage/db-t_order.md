# t_order — 物流订单主表

## 基本信息

| 字段 | 值 |
|------|-----|
| 存储类型 | 关系型数据库 (MySQL) |
| 模块 | logistics-order |
| 数据库 | logistics_db |
| 负责人 | 后端开发 |
| 需求来源 | REQ-LO-001, REQ-LO-005 |
| 版本 | v1.0 |

## 字段定义

| 字段 | 类型 | 索引 | 写入来源 | 读取去向 | 业务规则 | 说明 |
|------|------|------|---------|---------|---------|------|
| order_id | varchar(32) | PK | POST /orders | GET /orders, PUT /status, POST /confirm-charges | UUID 生成 | 主键 |
| order_no | varchar(20) | UNIQUE | POST /orders | GET /orders(搜索), order-list 页面, order-detail 页面 | 'LO-' + YYYYMMDD + '-' + 4位序号 | 业务编号 |
| customer_id | varchar(32) | INDEX | POST /orders | GET /orders(筛选) | 必须引用 t_customer.customer_id 且 status='active' | 客户 |
| origin | varchar(200) | — | POST /orders | order-detail 页面 | 不能为空 | 起运地 |
| destination | varchar(200) | — | POST /orders | order-detail 页面 | 不能为空 | 目的地 |
| transport_mode | varchar(20) | INDEX | POST /orders | order-list(筛选), order-detail | 枚举：sea/air/land/rail | 运输方式 |
| status | varchar(20) | INDEX | POST /orders(初始), PUT /status(流转), order-auto-close(超时) | GET /orders, order-list, order-detail | 初始='draft'; 状态机见 PUT-orders-status.md | 状态 |
| total_amount | decimal(12,2) | — | POST /orders(计算), POST /confirm-charges(可调整) | order-detail, POST /invoices | = Σ(t_charge_item.amount WHERE order_id=this) | 总金额 |
| remark | text | — | POST /orders | order-detail | 可为空 | 备注 |
| created_at | datetime | INDEX | POST /orders | order-list(排序) | 自动生成 | 创建时间 |
| updated_at | datetime | — | 每次 UPDATE | order-detail | 自动更新 | 更新时间 |

## 状态流转

```
draft ──→ accepted ──→ in_transit ──→ delivered ──→ charges_confirmed
                                          │
                                          └──→ auto_closed (超时7天)
```

## 关联接口

| 接口 | 操作 | 涉及字段 |
|------|------|---------|
| POST /api/v1/orders | INSERT | 全部字段 |
| GET /api/v1/orders | SELECT | 全部字段 |
| GET /api/v1/orders/{id} | SELECT | 全部字段 |
| PUT /api/v1/orders/{id}/status | UPDATE | status, updated_at |
| POST /api/v1/orders/{id}/confirm-charges | UPDATE | total_amount, status, updated_at |

## 关联定时任务

| 任务 | 操作 | 条件 |
|------|------|------|
| order-auto-close | UPDATE status='auto_closed' | status='delivered' AND updated_at < 7天前 |

## 关联表

| 表 | 关系 | 关联字段 | 数据流向 |
|-----|------|---------|---------|
| t_service_item | 一对多 | order_id | order → service_item（创建时同步写入） |
| t_charge_item | 一对多 | order_id | order → charge_item（创建时同步写入）; charge_item → order（汇总 total_amount） |
| t_customer | 多对一 | customer_id | customer → order（验证客户有效性） |

## 关联其他存储

| 存储节点 | 类型 | 关系 | 说明 |
|---------|------|------|------|
| order:lock:{order_no} | Redis | 写入保护 | 创建时加锁防并发 |
| order.created | MQ | 创建后发消息 | 通知下游服务 |
| order.status.changed | MQ | 状态变更后发消息 | 通知财务/通知服务 |
| orders-index | ES | 搜索索引 | 同步到 ES 供列表搜索 |

## 多入口操作对比

### status 的多入口对比

| 入口 | 操作 | 业务规则 | 代码位置 | 前置条件 |
|------|------|---------|---------|---------|
| POST /orders | INSERT status='draft' | 新建订单固定 draft | `OrderService#createOrder` | — |
| PUT /orders/{id}/status | UPDATE status={target} | 必须符合状态机合法跳转 | `OrderService#updateStatus` | 当前状态在合法跳转表中 |
| POST /orders/{id}/confirm-charges | UPDATE status='charges_confirmed' | 费用确认后自动变更 | `OrderService#confirmCharges` | status='delivered' |
| order-auto-close 定时任务 | UPDATE status='auto_closed' | 超时自动关闭 | `OrderAutoCloseJob#execute` | status='delivered' AND updated_at < 7天前 |

### total_amount 的多入口对比

| 入口 | 操作 | 业务规则 | 代码位置 | 前置条件 |
|------|------|---------|---------|---------|
| POST /orders | INSERT total_amount=Σ(charge.amount) | 创建时自动汇总 | `OrderService#createOrder` | — |
| POST /orders/{id}/confirm-charges | UPDATE total_amount=Σ(charge.amount) | 确认时重新汇总（运营可能调整了收费项） | `OrderService#confirmCharges` | status='delivered' |

## 变更记录

| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 关联需求/缺陷 |
|------|------|--------|--------|--------|-------------|
| v1.0 | 2025-04-17 | 示范 | 无（新建） | 创建 t_order 表文档 | REQ-LO-001, REQ-LO-005 |
