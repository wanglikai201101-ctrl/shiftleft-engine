# 用户认证系统需求文档

## 一、项目概述

### 1.1 项目目标
开发一个用户认证系统，支持用户注册和登录功能。

### 1.2 技术栈

**后端**
- 语言：Python 3.10+
- 框架：FastAPI
- 数据库：PostgreSQL 5432 端口（空白库）
- ORM：SQLAlchemy
- 密码加密：bcrypt
- Token：JWT (python-jose)

**前端**
- 语言：TypeScript
- 框架：React / Vue（待定）
- HTTP 客户端：Axios
- 状态管理：待定

**部署**
- 容器化：Docker
- 数据库迁移：Alembic

---

## 二、功能需求

### 2.1 用户注册

**功能描述**
用户通过填写用户名、邮箱、密码完成注册。

**业务规则**
- 用户名：3-20 个字符，仅支持字母、数字、下划线
- 邮箱：必须符合标准邮箱格式
- 密码：至少 8 个字符，必须包含大写字母、小写字母和数字
- 用户名和邮箱必须唯一

**接口规范**
```
POST /api/auth/register
Content-Type: application/json

请求体：
{
  "username": "string",
  "email": "string",
  "password": "string"
}

成功响应（201）：
{
  "user_id": "uuid",
  "username": "string",
  "email": "string",
  "created_at": "datetime"
}

失败响应（400）：
{
  "error_code": "string",
  "message": "string"
}
```

**错误码**
- `USERNAME_EXISTS`: 用户名已存在
- `EMAIL_EXISTS`: 邮箱已被注册
- `INVALID_EMAIL`: 邮箱格式不正确
- `WEAK_PASSWORD`: 密码强度不足
- `INVALID_USERNAME`: 用户名格式不正确

---

### 2.2 用户登录

**功能描述**
用户通过用户名/邮箱和密码登录系统，获取访问令牌。

**业务规则**
- 支持使用用户名或邮箱登录
- 密码错误累计 5 次后锁定账户 15 分钟
- 登录成功返回 JWT Token，有效期 24 小时
- 记录登录日志（IP、时间、结果）

**接口规范**
```
POST /api/auth/login
Content-Type: application/json

请求体：
{
  "username": "string",  // 用户名或邮箱
  "password": "string"
}

成功响应（200）：
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "user_id": "uuid",
    "username": "string",
    "email": "string"
  }
}

失败响应（401）：
{
  "error_code": "string",
  "message": "string"
}
```

**错误码**
- `INVALID_CREDENTIALS`: 用户名或密码错误
- `ACCOUNT_LOCKED`: 账户已锁定，请稍后重试
- `USER_NOT_FOUND`: 用户不存在

---

### 2.3 获取当前用户信息

**功能描述**
通过 Token 获取当前登录用户的信息。

**接口规范**
```
GET /api/auth/me
Authorization: Bearer {access_token}

成功响应（200）：
{
  "user_id": "uuid",
  "username": "string",
  "email": "string",
  "created_at": "datetime"
}

失败响应（401）：
{
  "error_code": "TOKEN_INVALID",
  "message": "Token 无效或已过期"
}
```

---

### 3.2 登录日志表 (login_logs)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PRIMARY KEY | 日志唯一标识 |
| user_id | UUID | FOREIGN KEY | 关联用户 ID |
| ip_address | VARCHAR(45) | NOT NULL | 登录 IP 地址 |
| user_agent | TEXT | NULL | 浏览器信息 |
| result | VARCHAR(20) | NOT NULL | 登录结果：success/failed/locked |
| created_at | TIMESTAMP | DEFAULT NOW() | 登录时间 |

**索引**
- `idx_user_id`: user_id
- `idx_created_at`: created_at
- `idx_result`: result

---

## 四、安全设计

### 4.1 密码安全
- 使用 bcrypt 算法加密密码，cost factor = 12
- 密码不可逆，只能通过验证方式比对
- 传输过程使用 HTTPS 加密

### 4.2 Token 安全
- 使用 JWT (HS256) 签名
- Token 包含：user_id, username, exp (过期时间)
- Token 有效期：24 小时
- 每次请求验证 Token 签名和过期时间

### 4.3 防暴力破解
- 连续 5 次登录失败锁定账户 15 分钟
- 记录所有登录尝试（成功和失败）
- 可选：添加图形验证码（失败 3 次后）

### 4.4 输入验证
- 所有输入进行格式验证和长度限制
- 防止 SQL 注入（使用 ORM 参数化查询）
- 防止 XSS 攻击（前端输出转义）

---

## 五、前端页面设计

### 5.1 注册页面 (/register)

**页面元素**
- 用户名输入框（带实时格式验证）
- 邮箱输入框（带格式验证）
- 密码输入框（带强度提示）
- 确认密码输入框
- 注册按钮
- 跳转到登录页链接

**交互逻辑**
1. 实时验证输入格式
2. 密码强度可视化提示
3. 提交时显示 loading 状态
4. 成功后跳转到登录页并提示
5. 失败显示具体错误信息

---

### 5.2 登录页面 (/login)

**页面元素**
- 用户名/邮箱输入框
- 密码输入框
- 记住我复选框（可选）
- 登录按钮
- 跳转到注册页链接
- 忘记密码链接（可选）

**交互逻辑**
1. 提交时显示 loading 状态
2. 成功后保存 Token 到 localStorage
3. 跳转到首页/仪表板
4. 失败显示错误信息
5. 账户锁定时显示剩余时间

---

### 5.3 用户信息页面 (/profile)

**页面元素**
- 显示用户名、邮箱
- 显示注册时间
- 登出按钮

**交互逻辑**
1. 页面加载时调用 GET /api/auth/me
2. Token 无效时跳转到登录页
3. 点击登出清除 Token 并跳转

---

## 六、后端项目结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── config.py               # 配置文件
│   ├── database.py             # 数据库连接
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py             # User 模型
│   │   └── login_log.py        # LoginLog 模型
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py             # Pydantic schemas
│   │   └── auth.py             # 认证相关 schemas
│   ├── api/
│   │   ├── __init__.py
│   │   └── auth.py             # 认证路由
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py         # 密码加密、Token 生成
│   │   └── deps.py             # 依赖注入
│   └── utils/
│       ├── __init__.py
│       └── validators.py       # 输入验证工具
├── alembic/                    # 数据库迁移
│   └── versions/
├── tests/                      # 测试文件
├── requirements.txt            # Python 依赖
├── .env                        # 环境变量
└── Dockerfile                  # Docker 配置
```

---

## 七、前端项目结构

```
frontend/
├── src/
│   ├── api/
│   │   └── auth.ts             # 认证 API 调用
│   ├── components/
│   │   ├── LoginForm.tsx       # 登录表单组件
│   │   ├── RegisterForm.tsx    # 注册表单组件
│   │   └── PrivateRoute.tsx    # 路由守卫
│   ├── pages/
│   │   ├── Login.tsx           # 登录页
│   │   ├── Register.tsx        # 注册页
│   │   └── Profile.tsx         # 用户信息页
│   ├── types/
│   │   └── auth.ts             # TypeScript 类型定义
│   ├── utils/
│   │   ├── validators.ts       # 前端验证工具
│   │   └── token.ts            # Token 存储管理
│   ├── App.tsx
│   └── main.tsx
├── package.json
├── tsconfig.json
└── vite.config.ts
```

---

## 八、环境变量配置

### 8.1 后端 (.env)

```env
# 数据库配置
DATABASE_URL=postgresql://postgres:password@localhost:5432/auth_db

# JWT 配置
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 应用配置
APP_NAME=User Auth System
DEBUG=True
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

### 8.2 前端 (.env)

```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## 九、开发步骤

### 9.1 后端开发步骤

1. **初始化项目**
   ```bash
   mkdir backend && cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install fastapi uvicorn sqlalchemy psycopg2-binary python-jose[cryptography] passlib[bpython-multipart alembic
   ```

2. **创建数据库**
   ```bash
   psql -U postgres
   CREATE DATABASE auth_db;
   ```

3. **配置数据库连接** (database.py)
4. **创建数据模型** (models/)
5. **初始化 Alembic 并创建迁移**
   ```bash
   alembic init alembic
   alembic revision --autogenerate -m "Initial migration"
   alembic upgrade head
   ```

6. **实现认证逻辑** (core/security.py, api/auth.py)
7. **运行开发服务器**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

---

### 9.2 前端开发步骤

1. **初始化项目**
   ```bash
   npm create vite@latest frontend -- --template react-ts
   cd frontend
   npm install axios react-router-dom
   ```

2. **创建 API 客户端** (api/auth.ts)
3. **实现表单组件** (components/)
4. **实现页面** (pages/)
5. **配置路由和路由守卫**
6. **运行开发服务器**
   ```bash
   npm run dev
   ```

---

## 十、测试用例

### 10.1 注册功能测试

| 测试用例 | 输入 | 预期结果 |
|---------|------|---------|
| 正常注册 | 有效的用户名、邮箱、密码 | 201，返回用户信息 |
| 用户名重复 | 已存在的用户名 | 400，USERNAME_EXISTS |
| 邮箱重复 | 已存在的邮箱 | 400，EMAIL_EXISTS |
| 邮箱格式错误 | "invalid-email" | 400，INVALID_EMAIL |
| 密码强度不足 | "123456" | 400，WEAK_PASSWORD |
| 用户名格式错误 | "a" (太短) | 400，INVALID_USERNAME |

### 10.2 登录功能测试

| 测试用例 | 输入 | 预期结果 |
|---------|------|---------|
| 正常登录 | 正确的用户名和密码 | 200，返回 Token |
| 密码错误 | 错误的密码 | 401，INVALID_CREDENTIALS |
| 用户不存在 | 不存在的用户名 | 401，USER_NOT_FOUND |
| 连续失败 5 次 | 5 次错误密码 | 401，ACCOUNT_LOCKED |
| 锁定期间登录 | 锁定期间尝试登录 | 401，ACCOUNT_LOCKED |
| 锁定解除后登录 | 15 分钟后正确密码 | 200，返回 Token |

### 10.3 Token 验证测试

| 测试用例 | 输入 | 预期结果 |
|---------|------|---------|
| 有效 Token | 未过期的 Token | 200，返回用户信息 |
| 过期 Token | 过期的 Token | 401，TOKEN_INVALID |
| 无效 Token | 伪造的 Token | 401，TOKEN_INVALID |
| 无 Token | 不携带 Token | 401，TOKEN_REQUIRED |

---

## 十一、部署说明

### 11.1 Dockn**docker-compose.yml**
```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: auth_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:password@db:5432/auth_db
    depends_on:
      - db

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend

volumes:
  postgres_data:
```

### 11.2 生产环境注意事项

1. 修改 SECRET_KEY 为强随机字符串
2. 关闭 DEBUG 模式
3. 配置 HTTPS
4. 设置 CORS 白名单
5. 配置数据库备份
6. 添加日志监控
7. 配置反向代理 (Nginx)

---

## 十二、后续扩展功能

- 邮箱验证（注册后发送激活邮件）
- 忘记密码/重置密码
- 刷新 Token 机制
- OAuth 第三方登录（Google, GitHub）
- 用户角色和权限管理
- 用户资料编辑
- 头像上传
- 登录设备管理
- 两步验证 (2FA)

---

### 2.4 用户登出

**功能描述**
用户主动登出，使当前 Token 失效。

**接口规范**
```
POST /api/auth/logout
Authorization: Bearer {access_token}

成功响应（200）：
{
  "message": "登出成功"
}
```

---

## 三、数据库设计

### 3.1 用户表 (users)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PRIMARY KEY | 用户唯一标识 |
| username | VARCHAR(50) | UNIQUE, NOT NULL | 用户名 |
| email | VARCHAR(100) | UNIQUE, NOT NULL | 邮箱 |
| password_hash | VARCHAR(255) | NOT NULL | 密码哈希值 |
| failed_attempts | INTEGER | DEFAULT 0 | 登录失败次数 |
| locked_until | TIMESTAMP | NULL | 锁定截止时间 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT NOW() | 更新时间 |

**索引**
- `idx_username`: username
- `idx_email`: email
- `idx_locked_until`: locked_until (用于定时解锁查询)

