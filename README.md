# DTU 物联网平台

当前处于第一个开发迭代。需求见根目录设计文档；实施边界、阶段与验收见 [开发计划](docs/development-plan.md)。

## 当前交付

- `contracts/`：网关遥测二进制协议 v1 草案与可执行测试向量。
- `backend/`：Java 21 / Spring Boot 服务骨架与首批 PostgreSQL 迁移。
- `deploy/`：本地数据库、缓存和 MQTT Broker 的开发环境配置。
- `docs/`：架构决策与硬件验证清单。

当前实际进度与限制见 [第一个迭代进度](docs/sprint-01-progress.md)。

在接口和硬件选型完成前，不把当前骨架视为可上线系统。服务端运行需要 Maven 与 Docker，当前工作机尚未安装或开放这两项工具。
