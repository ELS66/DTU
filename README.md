# DTU 物联网平台

当前处于第一个开发迭代。需求见根目录设计文档；实施边界、阶段与验收见 [开发计划](docs/development-plan.md)。

## 当前交付

- `contracts/`：网关遥测二进制协议、配置快照哈希规范与 Python/Node 共享测试向量。
- `dtu-simulator/`：无需真实设备的协议状态机与离线往返演示。
- `backend/`：Node.js + TypeScript / Fastify 服务骨架与首批 PostgreSQL 迁移。
- `admin-web/`、`h5-web/`：Vue 3 管理端和移动端界面骨架，可独立构建。
- `deploy/`：本地数据库、缓存和 MQTT Broker 的开发环境配置。
- `docs/`：架构决策与硬件验证清单。

当前实际进度与限制见 [第一个迭代进度](docs/sprint-01-progress.md)。

在接口和硬件选型完成前，不把当前骨架视为可上线系统。后端可在 `backend/` 运行 `npm ci`、`npm test` 和 `npm start`；两个前端目录各自运行 `npm ci`、`npm run dev` 或 `npm run build`。数据库迁移及完整业务功能仍在开发。
