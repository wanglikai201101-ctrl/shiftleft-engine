# REQ-LO-005 — 订单状态流转

## 需求概述

| 字段 | 值 |
|------|-----|
| 编号 | REQ-LO-005 |
| 名称 | 订单状态流转 |
| 来源 | PRD-物流核心流程 v2.0 |
| 优先级 | P0 |
| 负责人 | 产品经理 |
| 模块 | logistics-order |
| 版本 | v1.0 |

## 最小可测单元拆解

| 测试点 ID | 测试点描述 | 类型 | 前置条件 | 操作步骤 | 预期结果 | 验证方式 |
|-----------|----------|------|---------|---------|---------|---------|
| TP-LO-005-01 | 新建→已接单 | 功能 | 订单 status=draft | 调用 PUT /orders/{id}/status body={status:'accepted'} | status 变为 accepted | DB: t_order.status='accepted' |
| TP-LO-005-02 | 已接单→运输中 | 功能 | status=accepted | 更新状态为 in_transit | status=in_transit | DB + MQ: order.status.changed 消息 |
| TP-LO-005-03 | 运输中→已送达 | 功能 | status=in_transit | 更新状态为 delivered | status=delivered | DB + MQ |
| TP-LO-005-04 | 已送达→费用已确认 | 功能 | status=delivered | 确认收费项 | status=charges_confirmed | DB + API: POST /orders/{id}/confirm-charges |
| TP-LO-005-05 | 非法状态跳转被拒绝 | 异常 | status=draft | 直接更新为 delivered | 返回 400 "非法状态跳转" | API: 400 响应 |
| TP-LO-005-06 | 状态变更发送MQ事件 | 功能 | 任意合法状态变更 | 更新状态 | order.status.changed topic 收到消息，含 old_status 和 new_status | LOG: MQ 发送日志 |
| TP-LO-005-07 | 超时未确认自动关闭 | 功能 | status=delivered 超过 7 天 | 等待定时任务执行 | status=auto_closed | DB: t_order.status='auto_closed' |

## 关联实现

### 关联接口

| 测试点 ID | 接口 | 接口文档 |
|-----------|------|---------|
| TP-LO-005-01~05 | PUT /api/v1/orders/{id}/status | [apis/PUT-orders-status.md](../apis/PUT-orders-status.md) |
| TP-LO-005-04 | POST /api/v1/orders/{id}/confirm-charges | [apis/POST-orders-confirm-charges.md](../apis/POST-orders-confirm-charges.md) |

### 关联存储

| 测试点 ID | 存储节点 | 存储文档 |
|-----------|---------|----------|
| TP-LO-005-01~07 | t_order.status | [storage/db-t_order.md](../storage/db-t_order.md) |
| TP-LO-005-06 | order.status.changed (MQ) | [storage/mq-order-status-changed.md](../storage/mq-order-status-changed.md) |

### 关联定时任务

| 测试点 ID | 任务 | 任务文档 |
|-----------|------|---------|
| TP-LO-005-07 | order-auto-close | [jobs/order-auto-close.md](../jobs/order-auto-close.md) |

### 关联前端页面

| 测试点 ID | 页面 | 关键元素 | 页面文档 |
|-----------|------|---------|---------|
| TP-LO-005-01~04 | order-detail | order-detail-select-status | [pages/order-detail.md](../pages/order-detail.md) |

## 变更记录

| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 影响范围 |
|------|------|--------|--------|--------|---------|
| v1.0 | 2026-05-17 | 示范 | 无（新建） | 创建状态流转需求，拆解 7 个测试点 | 新建全部关联文档 |
