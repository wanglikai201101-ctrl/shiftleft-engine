# t_service_item — 订单服务项

## 基本信息

| 字段 | 值 |
|------|-----|
| 存储类型 | 关系型数据库 (MySQL) |
| 模块 | logistics-order |
| 负责人 | 后端开发 |
| 需求来源 | REQ-LO-001 |
| 版本 | v1.0 |

## 字段定义

| 字段 | 类型 | 索引 | 写入来源 | 读取去向 | 业务规则 | 说明 |
|------|------|------|---------|---------|---------|------|
| service_item_id | varchar(32) | PK | POST /orders | GET /orders/{id} | UUID | 主键 |
| order_id | varchar(32) | INDEX | POST /orders | GET /orders/{id}(关联查询) | 外键 → t_order.order_id | 所属订单 |
| catalog_id | varchar(32) | — | POST /orders | — | 引用服务目录 | 服务目录 ID |
| service_name | varchar(100) | — | POST /orders(从 catalog 查询) | order-detail 页面 | 从 t_service_catalog.name 复制 | 服务名称 |
| quantity | decimal(10,2) | — | POST /orders(用户输入) | order-detail 页面 | > 0 | 数量 |
| unit | varchar(20) | — | POST /orders(从 catalog 查询) | order-detail 页面 | kg/cbm/件 | 单位 |

## 关联表

| 表 | 关系 | 关联字段 | 数据流向 |
|-----|------|---------|---------|
| t_order | 多对一 | order_id | order → service_item |
| t_charge_item | 一对多 | service_item_id | service_item → charge_item（每个服务项生成 1~N 个收费项） |

## 变更记录

| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 关联需求/缺陷 |
|------|------|--------|--------|--------|-------------|
| v1.0 | 2025-04-17 | 示范 | 无（新建） | 创建服务项表文档 | REQ-LO-001 |
