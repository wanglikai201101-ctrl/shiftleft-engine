# order-auto-close — 订单超时自动关闭

## 基本信息

| 字段 | 值 |
|------|-----|
| 模块 | logistics-order |
| Cron | 0 0 2 * * * (每天凌晨 2 点) |
| 代码位置 | `OrderAutoCloseJob#execute — 扫描超时订单，批量更新状态为 auto_closed` |
| 负责人 | 后端开发 |
| 需求来源 | REQ-LO-005 (TP-LO-005-07) |
| 版本 | v1.0 |

## 数据流转

```
t_order (status='delivered', updated_at < 7天前)
  → 批量 UPDATE status='auto_closed', updated_at=NOW()
  → 逐条发送 MQ order.status.changed (old='delivered', new='auto_closed')
  → 写入 t_operation_log (记录自动关闭操作)
```

## 触发与取消条件

| 条件 | 来源 | 说明 |
|------|------|------|
| 触发 | PUT /orders/{id}/status 将状态改为 delivered | 送达后进入 7 天倒计时 |
| 取消 | POST /orders/{id}/confirm-charges | 费用确认后 status→charges_confirmed，不再满足 delivered 条件 |

## 关联数据库

| 表 | 操作 | 字段 | 业务规则 |
|-----|------|------|---------|
| t_order | SELECT | status, updated_at | WHERE status='delivered' AND updated_at < NOW() - 7 days |
| t_order | UPDATE | status='auto_closed', updated_at=NOW() | 批量更新，每批 100 条 |

## 关联其他存储

| 存储节点 | 类型 | 关系 | 说明 |
|---------|------|------|------|
| order.status.changed | MQ | 状态变更后发消息 | 每条关闭的订单发一条消息 |

## 监控

| 指标 | 阈值 | 告警方式 |
|------|------|---------|
| 单次关闭数 | > 500 | 钉钉告警（可能是批量异常） |
| 执行耗时 | > 120s | 日志告警 |
| 执行失败 | 任何异常 | 钉钉 + 邮件 |

## 变更记录

| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 关联需求/缺陷 |
|------|------|--------|--------|--------|-------------|
| v1.0 | 2025-04-17 | 示范 | 无（新建） | 创建自动关闭任务文档 | REQ-LO-005 |
