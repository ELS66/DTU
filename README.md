# DTU 物联网平台

当前处于第一个开发迭代。需求见根目录设计文档；实施边界、阶段与验收见 [开发计划](docs/development-plan.md)。

## 当前交付

- [Mac mini 换机开发说明](docs/mac-development.md)：全量资料同步、LFS 按需下载及 ESP-IDF 5.5.1 本机环境准备。

- [ESP32-C5固件工程与台架调试说明](c5/README.md)：0.7.0-dev，新增本地RAM故障记录/分页导出和电脑主板模拟器；[首板工具与接线步骤](docs/c5-local-diagnostics-and-bench.md)、[板内控制与待办](docs/c5-board-control-requirements-v0.14.4.md)。MQTT后端方案已确认，接入等用户文档，工程入口为c5/。

- [硬件 V0.14.4 最终资料与历史归档](PCB/README.md)。
- [V0.14.4焊接与首板上电检查](output/pdf/DTU-V0.14.4-焊接注意与首板上电检查.pdf) · [文字版](docs/v0.14.4-assembly-checklist.md)：PCB已到货，先进行装配和首板验证；软件暂留0.7.0-dev。

- [V0.14.4物联网模块软件需求R4](docs/iot-module-firmware-requirements-v0.14.4.md)、[串口协议1.8分析](docs/iot-module-uart-protocol-v1.8-review.md)与[确认记录/剩余问题](docs/esp32-firmware-confirmations-v0.14.4.md)：一对一设备模块，TTL优先、Wi-Fi含5GHz+4G、SmartConfig、每10秒记录余时、MQTT自有后端；原通用DTU方案保留作参考。

- `contracts/`：网关遥测二进制协议、配置快照哈希规范与 Python/Node 共享测试向量。
- `dtu-simulator/`：无需真实设备的协议状态机与离线往返演示。
- `backend/`：Node.js + TypeScript / Fastify 服务骨架与首批 PostgreSQL 迁移。
- `admin-web/`、`h5-web/`：Vue 3 管理端和移动端界面骨架，可独立构建。
- `deploy/`：本地数据库、缓存和 MQTT Broker 的开发环境配置。
- `docs/`：架构决策与硬件验证清单。

当前实际进度与限制见 [第一个迭代进度](docs/sprint-01-progress.md)。

在接口和硬件选型完成前，不把当前骨架视为可上线系统。后端使用方法及首批身份接口见 [后端说明](backend/README.md)；两个前端目录各自运行 `npm ci`、`npm run dev` 或 `npm run build`。数据库迁移及完整业务功能仍在开发。
