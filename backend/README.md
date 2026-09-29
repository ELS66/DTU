# 后端开发说明

在本目录运行 `npm ci`、`npm test`、`npm start`。不设置 `DATABASE_URL` 时仅启动健康检查；设置后注册首批身份接口，使用 `pg` 连接 PostgreSQL。启动前需按 V1、V2、V3 顺序执行 `migrations/` 中的 SQL。当前环境尚未实测数据库迁移。

## 首批身份接口

- `POST /api/v1/auth/login`：提交 `loginName`、`password`，返回 12 小时有效的 Bearer token。数据库只保存其 SHA-256 摘要。
- `POST /api/v1/auth/logout`：撤销当前 token。
- `GET /api/v1/me`：返回当前账号和租户成员关系。
- `GET /api/v1/tenants/{tenantId}/projects`：租户管理员可见该租户所有项目；普通用户仅可见自己加入的项目。每次请求从数据库重新核对账号状态和成员关系。

`app_user.password_hash` 使用 `scrypt$N$r$p$salt$hash` 格式。当前仅有密码哈希函数与登录验证，没有用户创建、密码重置、刷新 token、登录限速、审计或完整前端登录流程；这组接口仍属于开发阶段，不应直接作为公开登录服务上线。
