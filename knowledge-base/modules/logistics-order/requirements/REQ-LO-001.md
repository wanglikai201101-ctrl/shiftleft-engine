# REQ-LO-001 — 创建物流订单

## 需求概述

| 字段 | 值 |
|------|-----|
| 编号 | REQ-LO-001 |
| 名称 | 创建物流订单 |
| 来源 | PRD-物流核心流程 v2.0 |
| 优先级 | P0 |
| 负责人 | 产品经理 |
| 模块 | logistics-order |
| 版本 | v1.0 |

## 最小可测单元拆解

| 测试点 ID | 测试点描述 | 类型 | 前置条件 | 操作步骤 | 预期结果 | 验证方式 |
|-----------|----------|------|---------|---------|---------|---------|
| TP-LO-001-01 | 选择客户后自动填充客户信息 | 功能 | 已登录，在创建订单页 | 选择客户"ABC物流" | 客户编号、联系人、联系电话自动填充 | UI: order-create-text-customer-code 值非空 |
| TP-LO-001-02 | 添加服务项后自动生成收费项 | 功能 | 已选择客户 | 添加"国际运输"服务项 | 自动生成运费收费项，金额=费率×重量 | UI: order-create-table-charges 行数≥1 |
| TP-LO-001-03 | 必填字段为空时无法提交 | 异常 | 在创建订单页 | 不填起运地，点击提交 | 提示"请填写起运地" | UI: 错误提示文案 |
| TP-LO-001-04 | 提交成功后生成订单号 | 功能 | 所有必填字段已填写 | 点击提交 | 返回订单号（格式 LO-YYYYMMDD-XXXX），跳转详情页 | API: POST /orders 返回 201 + order_no |
| TP-LO-001-05 | 提交后服务项和收费项正确写入 | 功能 | 添加了2个服务项 | 提交订单 | t_service_item 2条记录，t_charge_item ≥2条记录 | DB: SELECT COUNT(*) FROM t_service_item WHERE order_id=? |
| TP-LO-001-06 | 订单总金额=所有收费项之和 | 功能 | 添加了运输+报关服务 | 提交订单 | t_order.total_amount = Σ(charge_item.amount) | DB: 对比 total_amount 和 SUM(amount) |
| TP-LO-001-07 | 并发创建不产生重复订单号 | 性能 | — | 2个用户同时提交 | 订单号不重复 | DB: SELECT order_no 无重复 |
| TP-LO-001-08 | 创建后发送MQ事件 | 功能 | — | 提交订单 | order.created topic 收到消息 | LOG: MQ 发送日志 |
| TP-LO-001-09 | 收费项金额精度为2位小数 | 边界 | — | 费率=0.333，重量=100 | 金额=33.30（四舍五入） | DB: t_charge_item.amount 精度检查 |
| TP-LO-001-10 | 无服务项时无法提交 | 异常 | 未添加任何服务项 | 点击提交 | 提示"请至少添加一个服务项" | UI: 错误提示文案 |

## 关联实现（追溯链）

### 关联接口

| 测试点 ID | 接口 | 接口文档 |
|-----------|------|---------|
| TP-LO-001-01 | GET /api/v1/customers | [apis/GET-customers.md](../apis/GET-customers.md) |
| TP-LO-001-02 | GET /api/v1/service-catalog | [apis/GET-service-catalog.md](../apis/GET-service-catalog.md) |
| TP-LO-001-04~08 | POST /api/v1/orders | [apis/POST-orders.md](../apis/POST-orders.md) |

### 关联数据库

| 测试点 ID | 表 | 存储文档 |
|-----------|-----|----------|
| TP-LO-001-05 | t_service_item | [storage/db-t_service_item.md](../storage/db-t_service_item.md) |
| TP-LO-001-05,06,09 | t_charge_item | [storage/db-t_charge_item.md](../storage/db-t_charge_item.md) |
| TP-LO-001-04,06 | t_order | [storage/db-t_order.md](../storage/db-t_order.md) |

### 关联其他存储

| 测试点 ID | 存储节点 | 存储文档 |
|-----------|---------|----------|
| TP-LO-001-07 | order:lock:{order_no} | [storage/redis-order-lock.md](../storage/redis-order-lock.md) |
| TP-LO-001-08 | order.created (MQ) | [storage/mq-order-created.md](../storage/mq-order-created.md) |

### 关联前端页面

| 测试点 ID | 页面 | 关键元素(data-testid) | 页面文档 |
|-----------|------|----------------------|---------|
| TP-LO-001-01 | order-create | order-create-select-customer | [pages/order-create.md](../pages/order-create.md) |
| TP-LO-001-02 | order-create | order-create-btn-add-service, order-create-table-charges | [pages/order-create.md](../pages/order-create.md) |
| TP-LO-001-03,10 | order-create | order-create-btn-submit | [pages/order-create.md](../pages/order-create.md) |
| TP-LO-001-04 | order-detail | — (跳转目标) | [pages/order-detail.md](../pages/order-detail.md) |

## 变更记录

| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 影响范围 |
|------|------|--------|--------|--------|---------|
| v1.0 | 2025-04-17 | 示范 | 无（新建） | 创建需求文档，拆解 10 个测试点 | 新建全部关联文档 |
