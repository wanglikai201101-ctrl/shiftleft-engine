# order.created — 订单创建事件

## 基本信息

| 字段 | 值 |
|------|-----|
| 存储类型 | MQ (Kafka) |
| 模块 | logistics-order |
| Topic | order.created |
| 消息格式 | JSON |
| 负责人 | 后端开发 |
| 需求来源 | REQ-LO-001 (TP-LO-001-08) |
| 版本 | v1.0 |

## 消息结构

| 字段 | 类型 | 必填 | 来源 | 说明 |
|------|------|------|------|------|
| order_id | string | 是 | t_order.order_id | 订单 ID |
| order_no | string | 是 | t_order.order_no | 订单号 |
| customer_id | string | 是 | t_order.customer_id | 客户 ID |
| total_amount | number | 是 | t_order.total_amount | 总金额 |
| service_count | integer | 是 | COUNT(t_service_item) | 服务项数量 |
| created_at | string | 是 | t_order.created_at | ISO 8601 |

## 生产者

| 生产者 | 触发条件 | 代码位置 | 业务规则 |
|--------|---------|---------|---------|
| POST /api/v1/orders | 订单写入 t_order 成功后 | `OrderService#createOrder` | 事务提交后发送，保证数据库已落盘 |

## 消费者

| 消费者 | 处理逻辑 | 代码位置 | 幂等策略 | 失败处理 |
|--------|---------|---------|---------|---------|
| 通知服务 | 发送订单创建通知（邮件/钉钉） | `NotifyConsumer#onOrderCreated` | order_id 去重 | 重试 3 次后丢弃 |
| 费控服务 | 预检费用额度 | `CostControlConsumer#onOrderCreated` | order_id 去重 | 重试 3 次后转死信队列 |

## 消息生命周期

| 阶段 | 说明 |
|------|------|
| 保留时间 | Kafka 7 天 |
| 死信队列 | order.created.dlq |
| 重试策略 | 3 次，间隔 1s/5s/30s |

## 关联其他存储

| 存储节点 | 类型 | 关系 | 说明 |
|---------|------|------|------|
| t_order | 数据库 | 消息数据来源 | 消息字段从 t_order 读取 |

## 变更记录

| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 关联需求/缺陷 |
|------|------|--------|--------|--------|-------------|
| v1.0 | 2025-04-17 | 示范 | 无（新建） | 创建 MQ 事件文档 | REQ-LO-001 |
