# 用户认证模块（user-auth）

> 版本：v1.0 | 创建时间：2026-04-23 | 负责人：示例团队

## 业务概述

用户认证是系统的基础能力，提供用户注册、登录、Token 验证和登出功能。

核心实体：
- **用户（User）**：系统用户，包含用户名、邮箱、密码哈希
- **登录日志（LoginLog）**：记录每次登录尝试的 IP、结果、时间

关系：用户 1:N 登录日志

## 需求追溯

| 需求编号 | 需求名称 | 涉及接口 | 涉及表 | 涉及页面 |
|---------|---------|---------|--------|---------|
| REQ-UA-001 | 用户注册与登录 | POST /api/auth/register, POST /api/auth/login, GET /api/auth/me, POST /api/auth/logout | users, login_logs | register, login, profile |

## 模块资产清单

| 类型 | 数量 | 目录 |
|------|------|------|
| 需求文档 | 1 | requirements/ |
| 接口文档 | 0（待生成） | apis/ |
| 存储文档 | 0（待生成） | storage/ |
| 页面文档 | 0（待生成） | pages/ |
