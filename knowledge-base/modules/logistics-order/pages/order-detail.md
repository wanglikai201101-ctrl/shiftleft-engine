# order-detail — 物流订单详情页

## 基本信息

| 字段 | 值 |
|------|-----|
| 模块 | logistics-order |
| 路由 | /orders/{id} |
| 组件 | OrderDetailPage.vue |
| 负责人 | 前端开发 |
| 需求来源 | REQ-LO-003, REQ-LO-004, REQ-LO-005 |
| 版本 | v1.0 |

## 页面元素清单（🔒 强制）

| data-testid | 元素类型 | 功能 | 触发接口 | 绑定字段 | 数据来源 |
|-------------|---------|------|---------|---------|---------|
| order-detail-text-order-no | text | 订单号 | — | ← `order_no` | GET /orders/{id} |
| order-detail-text-status | text | 状态标签 | — | ← `status` | GET /orders/{id} |
| order-detail-text-customer | text | 客户名称 | — | ← `customer.name` | GET /orders/{id} |
| order-detail-text-origin | text | 起运地 | — | ← `origin` | GET /orders/{id} |
| order-detail-text-destination | text | 目的地 | — | ← `destination` | GET /orders/{id} |
| order-detail-text-transport | text | 运输方式 | — | ← `transport_mode` | GET /orders/{id} |
| order-detail-table-services | table | 服务项列表 | — | ← `service_items[]` | GET /orders/{id} |
| order-detail-table-charges | table | 收费项列表 | — | ← `charge_items[]` | GET /orders/{id} |
| order-detail-text-total | text | 总金额 | — | ← `total_amount` | GET /orders/{id} |
| order-detail-select-status | select | 状态变更 | PUT /orders/{id}/status | → `status` 参数 | 枚举（根据当前状态过滤合法选项） |
| order-detail-btn-update-status | btn | 确认状态变更 | PUT /orders/{id}/status | — | — |
| order-detail-btn-confirm-charges | btn | 确认费用 | POST /orders/{id}/confirm-charges | — | 仅 status=delivered 时显示 |
| order-detail-btn-edit-charge | btn | 编辑收费项 | — | — | 仅 status=delivered 时可操作 |
| order-detail-input-adjusted-amount | input | 调整金额 | — | → `adjusted_amount` | 运营手动输入 |

## 接口调用顺序

页面加载：
1. `GET /api/v1/orders/{id}` — 订单详情（含服务项和收费项）

状态变更：
1. `PUT /api/v1/orders/{id}/status` — 更新状态
2. `GET /api/v1/orders/{id}` — 刷新页面

费用确认：
1. （可选）运营编辑收费项金额
2. `POST /api/v1/orders/{id}/confirm-charges` — 确认费用
3. `GET /api/v1/orders/{id}` — 刷新页面

## 数据流转

| 数据 | 来源 | 展示元素 | 流向 |
|------|------|---------|------|
| order_no | GET /orders/{id} | order-detail-text-order-no | 仅展示 |
| status | GET /orders/{id} | order-detail-text-status | → PUT /status 的前置校验 |
| total_amount | GET /orders/{id} | order-detail-text-total | → POST /invoices |
| charge_items[].amount | GET /orders/{id} | order-detail-table-charges | 运营可编辑 → POST /confirm-charges |

## 变更记录

| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 关联需求/缺陷 |
|------|------|--------|--------|--------|-------------|
| v1.0 | 2025-04-17 | 示范 | 无（新建） | 创建详情页文档，14 个元素 | REQ-LO-003, REQ-LO-004, REQ-LO-005 |
