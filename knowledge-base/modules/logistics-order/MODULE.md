# 物流订单模块（logistics-order）

> 版本：v1.0 | 创建时间：2026-04-17 | 负责人：示范模块

## 业务概述

物流订单是核心业务实体，一个订单包含：
- **基本信息**：客户、起运地、目的地、运输方式
- **服务项（Service Items）**：订单包含的物流服务（如运输、报关、仓储、保险）
- **收费项（Charge Items）**：每个服务项对应的费用明细（如运费、报关费、仓储费、保险费）

关系：订单 1:N 服务项 1:N 收费项

## 需求追溯

| 需求编号 | 需求名称 | 涉及接口 | 涉及表 | 涉及页面 |
|---------|---------|---------|--------|---------|
| REQ-LO-001 | 创建物流订单 | POST /orders, GET /customers, GET /service-catalog | t_order, t_service_item, t_charge_item, t_customer | order-create |
| REQ-LO-002 | 订单列表与搜索 | GET /orders | t_order, es-orders-index | order-list |
| REQ-LO-003 | 订单详情与编辑 | GET /orders/{id}, PUT /orders/{id} | t_order, t_service_item, t_charge_item | order-detail |
| REQ-LO-004 | 订单费用确认与账单生成 | POST /orders/{id}/confirm-charges, POST /invoices | t_order, t_charge_item, t_invoice | order-detail, invoice-list |
| REQ-LO-005 | 订单状态流转 | PUT /orders/{id}/status | t_order, mq-order-status-changed | order-detail |
| REQ-LO-006 | 超时未确认自动关闭 | — (定时任务) | t_order | — |

## 模块资产清单

| 类型 | 数量 | 目录 |
|------|------|------|
| 需求文档 | 2 | requirements/ |
| 接口文档 | 4 | apis/ |
| 存储文档 | 6 | storage/ |
| 定时任务文档 | 1 | jobs/ |
| 前端页面文档 | 3 | pages/ |

## 核心数据流

### 创建订单完整链路

```
1. 用户在 order-create 页面选择客户、填写起运地/目的地
   → 前端元素: order-create-select-customer, order-create-input-origin
2. 用户添加服务项（运输、报关等）
   → 前端元素: order-create-btn-add-service
3. 系统根据服务项自动生成收费项（费率表查询）
   → 接口: GET /service-catalog → 费率计算
4. 用户确认后提交
   → 接口: POST /api/v1/orders
5. 后端写入 t_order + t_service_item + t_charge_item
   → Redis: order:lock:{order_no} 防并发
6. 发送订单创建事件
   → MQ: order.created → 通知服务、费控服务消费
7. 跳转订单详情页
   → 页面: order-detail
```

### 费用确认链路

```
1. 运营在 order-detail 页面审核收费项
   → 前端元素: order-detail-btn-confirm-charges
2. 确认后生成账单
   → 接口: POST /api/v1/orders/{id}/confirm-charges
3. 更新订单状态为 charges_confirmed
   → MQ: order.status.changed → 财务系统消费
4. 生成发票
   → 接口: POST /api/v1/invoices
```
