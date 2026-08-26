# PUT /api/v1/orders/{id}/status — 订单状态变更

## 基本信息

| 字段 | 值 |
|------|-----|
| 模块 | logistics-order |
| 方法 | PUT |
| 路径 | /api/v1/orders/{id}/status |
| 认证 | Bearer Token |
| 代码位置 | `OrderService#updateStatus — 校验状态机合法性，更新状态，发送 MQ 事件` |
| 负责人 | 后端开发 |
| 需求来源 | REQ-LO-005 |
| 版本 | v1.0 |
| 最后更新 | 2025-04-17 |

## 请求参数

| 参数 | 类型 | 必填 | 来源 | 说明 |
|------|------|------|------|------|
| id | string (path) | 是 | GET /orders 返回的 order_id | 订单 ID |
| status | string (body) | 是 | 用户操作 | 目标状态：accepted/in_transit/delivered/charges_confirmed/auto_closed |
| remark | string (body) | 否 | 用户输入 | 状态变更备注 |

## 响应结构

| 字段 | 类型 | 流向 | 说明 |
|------|------|------|------|
| order_id | string | → order-detail 页面刷新 | 订单 ID |
| old_status | string | → MQ order.status.changed 消息体 | 变更前状态 |
| new_status | string | → order-detail 页面展示, → MQ 消息体 | 变更后状态 |
| updated_at | string | → order-detail 页面展示 | 变更时间 |

## 关联数据库

| 表 | 操作 | 字段 | 业务规则 | 说明 |
|-----|------|------|---------|------|
| t_order | SELECT | status | 查询当前状态，校验状态机 | 前置校验 |
| t_order | UPDATE | status, updated_at | 状态机：draft→accepted→in_transit→delivered→charges_confirmed; 非法跳转返回 400 | 更新状态 |

## 状态机（业务规则核心）

```
draft ──(接单)──→ accepted ──(发运)──→ in_transit ──(送达)──→ delivered
                                                                │
                                                    ┌───────────┤
                                                    │           │
                                              (费用确认)    (超时7天)
                                                    │           │
                                                    ▼           ▼
                                            charges_confirmed  auto_closed
```

合法跳转：

| 当前状态 | 允许跳转到 |
|---------|----------|
| draft | accepted |
| accepted | in_transit |
| in_transit | delivered |
| delivered | charges_confirmed, auto_closed |

## 关联其他存储

| 存储节点 | 类型 | 关系 | 说明 |
|---------|------|------|------|
| order.status.changed | MQ Topic | 状态变更后发消息 | 消息体含 order_id, old_status, new_status |

## 关联前端页面

| 页面 | 触发元素(data-testid) | 触发方式 |
|------|----------------------|---------|
| order-detail | order-detail-select-status | 下拉选择 + 确认 |

## 错误码

| 错误码 | 说明 | 前端处理 |
|--------|------|---------|
| 400010 | 订单不存在 | 提示"订单不存在" |
| 400011 | 非法状态跳转 | 提示"当前状态不允许此操作" |

## 变更记录

| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 关联需求/缺陷 |
|------|------|--------|--------|--------|-------------|
| v1.0 | 2025-04-17 | 示范 | 无（新建） | 创建状态变更接口文档 | REQ-LO-005 |
