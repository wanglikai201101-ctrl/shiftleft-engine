# POST /api/v1/orders — 创建物流订单

## 基本信息

| 字段 | 值 |
|------|-----|
| 模块 | logistics-order |
| 方法 | POST |
| 路径 | /api/v1/orders |
| 认证 | Bearer Token |
| 代码位置 | `OrderService#createOrder — 创建订单，写入服务项和收费项，计算总金额` |
| 负责人 | 后端开发 |
| 需求来源 | REQ-LO-001 |
| 版本 | v1.0 |
| 最后更新 | 2025-04-17 |

## 请求参数

| 参数 | 类型 | 必填 | 来源 | 说明 |
|------|------|------|------|------|
| customer_id | string | 是 | GET /customers 返回 | 客户 ID |
| origin | string | 是 | 用户输入 | 起运地 |
| destination | string | 是 | 用户输入 | 目的地 |
| transport_mode | string | 是 | 用户选择 | 运输方式：sea/air/land/rail |
| service_items | array | 是 | 用户添加 | 服务项列表 |
| service_items[].catalog_id | string | 是 | GET /service-catalog 返回 | 服务目录 ID |
| service_items[].quantity | number | 是 | 用户输入 | 数量（如重量 kg、体积 cbm） |
| service_items[].unit | string | 是 | GET /service-catalog 返回 | 单位：kg/cbm/件 |
| remark | string | 否 | 用户输入 | 备注 |

## 响应结构

| 字段 | 类型 | 流向 | 说明 |
|------|------|------|------|
| order_id | string | → GET /orders/{id}, → PUT /orders/{id}/status | 订单 ID |
| order_no | string | → order-detail 页面展示, → order-list 搜索 | 订单号 LO-YYYYMMDD-XXXX |
| status | string | → order-detail 页面展示 | 初始状态 draft |
| total_amount | number | → order-detail 页面展示, → POST /invoices | 总金额 = Σ收费项 |
| service_items | array | → order-detail 页面展示 | 服务项列表（含生成的收费项） |

## 依赖接口（上游）

| 接口 | 传递的字段 | 关系 |
|------|----------|------|
| GET /api/v1/customers | customer_id | 客户必须存在且状态为 active |
| GET /api/v1/service-catalog | catalog_id, unit_price, unit | 查询费率，计算收费项金额 |

## 被依赖接口（下游）

| 接口 | 消费的字段 | 关系 |
|------|----------|------|
| GET /api/v1/orders/{id} | order_id | 查询订单详情 |
| PUT /api/v1/orders/{id}/status | order_id | 状态流转 |
| POST /api/v1/orders/{id}/confirm-charges | order_id | 费用确认 |
| POST /api/v1/invoices | order_id, total_amount | 生成发票 |

## 关联数据库

| 表 | 操作 | 字段 | 业务规则 | 说明 |
|-----|------|------|---------|------|
| t_order | INSERT | order_id, order_no, customer_id, origin, destination, transport_mode, status, total_amount | order_no = 'LO-' + YYYYMMDD + '-' + 4位序号; status 初始 'draft'; total_amount = Σ(charge_item.amount) | 订单主表 |
| t_service_item | INSERT | service_item_id, order_id, catalog_id, service_name, quantity, unit | 每个 service_items[] 元素生成一条记录 | 服务项明细 |
| t_charge_item | INSERT | charge_item_id, order_id, service_item_id, charge_name, unit_price, quantity, amount | amount = unit_price × quantity，四舍五入保留 2 位小数 | 收费项明细 |
| t_customer | SELECT | customer_id, status | status 必须为 'active' | 验证客户有效性 |

## 关联其他存储

| 存储节点 | 类型 | 关系 | 说明 |
|---------|------|------|------|
| order:lock:{order_no} | Redis | 写入保护 | 防止并发创建重复订单号 |
| order.created | MQ Topic | 写入后发消息 | 订单创建成功后发送事件 |

## 关联前端页面

| 页面 | 触发元素(data-testid) | 触发方式 |
|------|----------------------|---------|
| order-create | order-create-btn-submit | 按钮点击 |
| order-detail | — | 创建成功后跳转 |

## 错误码

| 错误码 | 说明 | 前端处理 |
|--------|------|---------|
| 400001 | 客户不存在或已停用 | 提示"客户无效，请重新选择" |
| 400002 | 服务项列表为空 | 提示"请至少添加一个服务项" |
| 400003 | 服务目录不存在 | 提示"服务项无效" |
| 400004 | 必填字段缺失 | 提示具体缺失字段 |

## 变更记录

| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 关联需求/缺陷 |
|------|------|--------|--------|--------|-------------|
| v1.0 | 2025-04-17 | 示范 | 无（新建） | 创建接口文档 | REQ-LO-001 |
