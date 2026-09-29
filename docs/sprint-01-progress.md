# 第一个迭代进度

截至 2026-09-28：

| 任务 | 状态 | 证据 / 后续 |
|---|---|---|
| T01 决策与硬件清单 | 初稿完成 | `decision-log.md`、`hardware-support-matrix.md`；实际设备和电路待确认 |
| T02 骨架与环境 | 部分完成 | Node.js + TypeScript/Fastify 服务骨架可构建、健康检查通过；Compose 已写但当前机器无 Docker，前端骨架待做 |
| T03 模型迁移 | 草案完成 | V1、V2 PostgreSQL 迁移；没有本地数据库，尚未实跑迁移 |
| T04 协议契约 | 进行中 | 遥测、配置快照哈希、命令/回复/ACK 均有 Python 与 TypeScript 共享向量；C 实现、JSON Schema 与重试时限仍未完成 |
| T05 ESP32-S3 硬件探路 | 未开始 | 尚无开发板、具体模组和收发电路信息 |
| T11 网关模拟器 | MQTT 开发适配完成 | Python 内存状态机加入 MQTT 主题收发、周期采样、ACK 与补传；假客户端测试通过，真实 Broker 联调、掉电持久化和真机行为待做 |

下一步在可运行 PostgreSQL 的环境中验证迁移，并补前端骨架和 MQTT Broker 联调；硬件到位后启动串口与 OTA 空间验证。
