# order-list — 物流订单列表页

## 基本信息

| 字段 | 值 |
|------|-----|
| 模块 | logistics-order |
| 路由 | /orders |
| 组件 | OrderListPage.vue |
| 负责人 | 前端开发 |
| 需求来源 | REQ-LO-002 |
| 版本 | v1.0 |

## 页面元素清单（🔒 强制）

| data-testid | 元素类型 | 功能 | 触发接口 | 绑定字段 | 数据来源 |
|-------------|---------|------|---------|---------|---------|
| order-list-input-search | input | 搜索（订单号/客户名） | GET /orders?keyword= | → `keyword` 参数 | 用户输入 |
| order-list-select-status | select | 状态筛选 | GET /orders?status= | → `status` 参数 | 枚举值 |
| order-list-select-transport | select | 运输方式筛选 | GET /orders?transport_mode= | → `transport_mode` 参数 | 枚举值 |
| order-list-btn-search | btn | 搜索 | GET /orders | — | — |
| order-list-btn-create | btn | 新建订单 | 跳转 /orders/create | — | — |
| order-list-table-main | table | 订单列表 | GET /orders | ← `data[]` | 接口返回 |
| order-list-link-detail | link | 订单详情 | 跳转 /orders/{id} | ← `order_id` | 行数据 |
| order-list-text-status | text | 状态标签 | — | ← `status` | 行数据 |
| order-list-text-amount | text | 总金额 | — | ← `total_amount` | 行数据 |
| order-list-pagination | pagination | 分页 | GET /orders?page= | ← `total` | 接口返回 |

## 接口调用顺序

页面加载：
1. `GET /api/v1/orders?page=1&size=20` — 列表数据

搜索/筛选：
1. `GET /api/v1/orders?keyword={input}&status={select}&transport_mode={select}&page=1`

## 变更记录

| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 关联需求/缺陷 |
|------|------|--------|--------|--------|-------------|
| v1.0 | 2026-05-17 | 示范 | 无（新建） | 创建列表页文档，10 个元素 | REQ-LO-002 |
