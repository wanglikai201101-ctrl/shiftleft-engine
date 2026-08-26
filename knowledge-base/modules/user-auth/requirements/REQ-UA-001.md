# REQ-UA-001 — 用户注册与登录

## 需求概述

| 字段 | 值 |
|------|-----|
| 编号 | REQ-UA-001 |
| 名称 | 用户注册与登录 |
| 来源 | [用户认证系统需求文档](../../../docs/user-auth-requirements.md) |
| 优先级 | P0 |
| 负责人 | 示例团队 |
| 模块 | user-auth |
| 版本 | v1.0 |

## 业务规则定义

| 规则 ID | 规则名称 | 公式/逻辑 | 关联测试点 | 说明 |
|---------|---------|----------|-----------|------|
| BR-001 | 用户名格式 | len(username) in [3,20] AND regex(^[a-zA-Z0-9_]+$) | TP-UA-001-01, TP-UA-001-06 | 仅字母数字下划线 |
| BR-002 | 密码强度 | len(password) >= 8 AND has_upper AND has_lower AND has_digit | TP-UA-001-01, TP-UA-001-05 | 必须包含大小写和数字 |
| BR-003 | 唯一性约束 | username UNIQUE AND email UNIQUE | TP-UA-001-02, TP-UA-001-03 | 注册时校验 |
| BR-004 | 登录锁定 | IF failed_attempts >= 5 THEN lock 15min | TP-UA-001-10, TP-UA-001-11 | 防暴力破解 |
| BR-005 | Token 有效期 | exp = now() + 24h, algorithm = HS256 | TP-UA-001-13, TP-UA-001-14 | JWT 签名 |
| BR-006 | 密码加密 | bcrypt(password, cost=12) | TP-UA-001-01 | 不可逆存储 |

## 最小可测单元拆解

| 测试点 ID | 测试点描述 | 类型 | 前置条件 | 操作步骤 | 预期结果 | 验证方式 |
|-----------|----------|------|---------|---------|---------|---------|
| TP-UA-001-01 | 正常注册成功 | 功能 | 数据库无同名用户 | POST /api/auth/register，传入合法 username/email/password | 201，返回 user_id/username/email/created_at | API: status=201 + DB: users 表新增一行 |
| TP-UA-001-02 | 用户名重复注册失败 | 异常 | 已存在 username=testuser | POST /api/auth/register，username=testuser | 400，error_code=USERNAME_EXISTS | API: status=400 |
| TP-UA-001-03 | 邮箱重复注册失败 | 异常 | 已存在 email=test@example.com | POST /api/auth/register，email=test@example.com | 400，error_code=EMAIL_EXISTS | API: status=400 |
| TP-UA-001-04 | 邮箱格式错误 | 边界 | 无 | POST /api/auth/register，email=invalid-email | 400，error_code=INVALID_EMAIL | API: status=400 |
| TP-UA-001-05 | 密码强度不足 | 边界 | 无 | POST /api/auth/register，password=123456 | 400，error_code=WEAK_PASSWORD | API: status=400 |
| TP-UA-001-06 | 用户名格式错误（太短） | 边界 | 无 | POST /api/auth/register，username=a | 400，error_code=INVALID_USERNAME | API: status=400 |
| TP-UA-001-07 | 正常登录成功 | 功能 | 已注册用户 testuser | POST /api/auth/login，正确的 username+password | 200，返回 access_token + user 信息 | API: status=200 + token 可解码 |
| TP-UA-001-08 | 密码错误登录失败 | 异常 | 已注册用户 testuser | POST /api/auth/login，错误 password | 401，error_code=INVALID_CREDENTIALS | API: status=401 + DB: failed_attempts+1 |
| TP-UA-001-09 | 用户不存在登录失败 | 异常 | 无此用户 | POST /api/auth/login，username=nonexistent | 401，error_code=USER_NOT_FOUND | API: status=401 |
| TP-UA-001-10 | 连续5次失败后锁定 | 安全 | 已注册用户，failed_attempts=4 | POST /api/auth/login，第5次错误密码 | 401，error_code=ACCOUNT_LOCKED | API: status=401 + DB: locked_until 被设置 |
| TP-UA-001-11 | 锁定期间登录被拒 | 安全 | 用户已锁定，locked_until > now() | POST /api/auth/login，正确密码 | 401，error_code=ACCOUNT_LOCKED | API: status=401 |
| TP-UA-001-12 | 锁定解除后可登录 | 功能 | 用户锁定已过期（locked_until < now()） | POST /api/auth/login，正确密码 | 200，返回 token + failed_attempts 重置为 0 | API: status=200 + DB: failed_attempts=0 |
| TP-UA-001-13 | 有效 Token 获取用户信息 | 功能 | 已登录，持有有效 token | GET /api/auth/me，携带 Bearer token | 200，返回 user_id/username/email | API: status=200 |
| TP-UA-001-14 | 过期 Token 被拒绝 | 安全 | Token 已过期 | GET /api/auth/me，携带过期 token | 401，error_code=TOKEN_INVALID | API: status=401 |
| TP-UA-001-15 | 伪造 Token 被拒绝 | 安全 | 无 | GET /api/auth/me，携带伪造 token | 401，error_code=TOKEN_INVALID | API: status=401 |
| TP-UA-001-16 | 登出成功 | 功能 | 已登录 | POST /api/auth/logout，携带有效 token | 200，message=登出成功 | API: status=200 |
| TP-UA-001-17 | 登录记录日志 | 功能 | 已注册用户 | POST /api/auth/login（成功或失败） | login_logs 表新增一行，含 ip/result/user_id | DB: login_logs 新增记录 |

## 关联实现（追溯链）

### 关联接口

| 测试点 ID | 接口 | 接口文档 |
|-----------|------|---------|
| TP-UA-001-01~06 | POST /api/auth/register | [apis/POST-auth-register.md](../apis/POST-auth-register.md) |
| TP-UA-001-07~12, TP-UA-001-17 | POST /api/auth/login | [apis/POST-auth-login.md](../apis/POST-auth-login.md) |
| TP-UA-001-13~15 | GET /api/auth/me | [apis/GET-auth-me.md](../apis/GET-auth-me.md) |
| TP-UA-001-16 | POST /api/auth/logout | [apis/POST-auth-logout.md](../apis/POST-auth-logout.md) |

### 关联数据库

| 测试点 ID | 表 | 存储文档 |
|-----------|-----|----------|
| TP-UA-001-01~06 | users | [storage/db-users.md](../storage/db-users.md) |
| TP-UA-001-08, TP-UA-001-10~12 | users (failed_attempts, locked_until) | [storage/db-users.md](../storage/db-users.md) |
| TP-UA-001-17 | login_logs | [storage/db-login_logs.md](../storage/db-login_logs.md) |

### 关联前端页面

| 测试点 ID | 页面 | 关键元素(data-testid) | 页面文档 |
|-----------|------|----------------------|---------|
| TP-UA-001-01~06 | register | auth-register-input-username, auth-register-input-email, auth-register-input-password, auth-register-btn-submit | [pages/register.md](../pages/register.md) |
| TP-UA-001-07~12 | login | auth-login-input-username, auth-login-input-password, auth-login-btn-submit | [pages/login.md](../pages/login.md) |
| TP-UA-001-13~16 | profile | auth-profile-text-username, auth-profile-text-email, auth-profile-btn-logout | [pages/profile.md](../pages/profile.md) |

## 变更记录

| 版本 | 日期 | 修改人 | 修改前 | 修改后 | 影响范围 |
|------|------|--------|--------|--------|---------|
| v1.0 | 2026-04-23 | 示例团队 | 无（新建） | 从 PRD 转写为规范化需求文档，拆解 17 个测试点 | 新建：4 个接口、2 张表、3 个页面 |
