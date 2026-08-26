# order-create — 创建物流订单页

## 基本信息

| 字段 | 值 |
|------|-----|
| 模块 | logistics-order |
| 路由 | /orders/create |
| 组件 | OrderCreatePage.vue |
| 负责人 | 前端开发 |
| 需求来源 | REQ-LO-001 |
| 版本 | v1.0 |

## 页面元素清单（🔒 强制）

| data-testid | 元素类型 | 功能 | 触发接口 | 绑定字段 | 数据来源 |
|-------------|---------|------|---------|---------|---------|
| order-create-select-customer | select | 选择客户 | GET /customers | → `customer_id` 参数 | 接口返回客户列表 |
| order-create-text-customer-code | text | 客户编号（自动填充） | — | ← `customer.code` | 选择客户后填充 |
| order-create-input-origin | input | 起运地 | — | → `origin` 参数 | 用户输入 |
| order-create-input-destination | input | 目的地 | — | → `destination` 参数 | 用户输入 |
| order-create-select-transport | select | 运输方式 | — | → `transport_mode` 参数 | 枚举：海运/空运/陆运/铁路 |
| order-create-btn-add-service | btn | 添加服务项 | GET /service-catalog | — | 打开服务目录弹窗 |
| order-create-table-services | table | 服务项列表 | — | ← `service_items[]` | 用户添加 |
| order-create-table-charges | table | 收费项列表（自动生成） | — | ← 计算后的收费项 | 根据服务项+费率自动生成 |
| order-create-text-total | text | 总金额 | — | ← Σ(charge.amount) | 自动汇总 |
| order-create-input-remark | input | 备注 | — | → `remark` 参数 | 用户输入 |
| order-create-btn-submit | btn | 提交订单 | POST /orders | — | — |
| order-create-btn-cancel | btn | 取消 | — | — | 返回列表页 |

## 接口调用顺序

页面加载：
1. `GET /api/v1/customers?status=active` — 客户下拉列表数据

添加服务项：
1. `GET /api/v1/service-catalog?transport_mode={selected}` — 服务目录
2. 前端根据 catalog.unit_price × quantity 计算收费项（预览，非最终）

提交订单：
1. `POST /api/v1/orders` — 提交全部数据
2. 成功后跳转 `/orders/{order_id}` — 订单详情页

## 数据流转

| 数据 | 来源 | 展示元素 | 流向 |
|------|------|---------|------|
| customer_id | GET /customers | order-create-select-customer | → POST /orders 请求参数 |
| service_items | 用户添加 | order-create-table-services | → POST /orders 请求参数 |
| total_amount | 前端计算（预览） | order-create-text-total | 最终值由后端计算 |
| order_id | POST /orders 响应 | — | → 跳转 order-detail 页面 |

## 变更记录

| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 关联需求/缺陷 |
|------|------|--------|--------|--------|-------------|
| v1.0 | 2025-04-17 | 示范 | 无（新建） | 创建页面文档，12 个元素 | REQ-LO-001 |
