# 后端开发说明

在本目录运行 `npm ci`、`npm test`、`npm start`。不设置 `DATABASE_URL` 时仅启动健康检查；设置后注册首批身份接口，使用 `pg` 连接 PostgreSQL。当前环境尚未实测数据库迁移。

## 首次启动数据库

1. 设置 `DATABASE_URL`，指向专用的空 PostgreSQL 数据库。
2. 运行 `npm run migrate`。命令按 V1、V2、V3 顺序应用迁移，记录 SHA-256 校验和；重复运行会跳过已应用文件，文件被改动或迁移失败时会拒绝继续。当前版本在一个事务中执行所有待应用迁移。
3. 设置 `DTU_BOOTSTRAP_PASSWORD` 为至少 12 字符的初始密码，再运行 `npm run bootstrap -- --login admin --tenant "租户名称"`。命令只允许在没有用户和租户的数据库上执行，创建首个租户管理员后应清除该环境变量。
4. 运行 `npm start`，使用登录接口获取 token。

在 PowerShell 中可用 `Read-Host -AsSecureString` 读取密码，转换为本次进程的环境变量后运行初始化命令，随后执行 `Remove-Item Env:DTU_BOOTSTRAP_PASSWORD`。不要把密码放进命令参数、代码仓库或日志。

## 首批身份接口

- `POST /api/v1/auth/login`：提交 `loginName`、`password`，返回 12 小时有效的 Bearer token。数据库只保存其 SHA-256 摘要。
- `POST /api/v1/auth/logout`：撤销当前 token。
- `GET /api/v1/me`：返回当前账号和租户成员关系。
- `GET /api/v1/tenants/{tenantId}/projects`：租户管理员可见该租户所有项目；普通用户仅可见自己加入的项目。每次请求从数据库重新核对账号状态和成员关系。

`app_user.password_hash` 使用 `scrypt$N$r$p$salt$hash` 格式。当前仅有首个管理员初始化，没有后续用户创建、密码重置、刷新 token、登录限速、审计或完整前端登录流程；这组接口仍属于开发阶段，不应直接作为公开登录服务上线。
