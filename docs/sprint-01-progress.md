# 第一个迭代进度

截至 2026-09-28：

| 任务 | 状态 | 证据 / 后续 |
|---|---|---|
| T01 决策与硬件清单 | 初稿完成 | `decision-log.md`、`hardware-support-matrix.md`；实际设备和电路待确认 |
| T02 骨架与环境 | 部分完成 | Node.js + TypeScript/Fastify 服务骨架可构建、健康检查通过；Compose 已写但当前机器无 Docker，前端骨架待做 |
| T03 模型迁移 | 草案完成 | V1、V2 PostgreSQL 迁移；没有本地数据库，尚未实跑迁移 |
| T04 协议契约 | 进行中 | Python 与后端 TypeScript 遥测解码通过同一 golden vector；C 实现、配置/命令规范化仍未完成 |
| T05 ESP32-S3 硬件探路 | 未开始 | 尚无开发板、具体模组和收发电路信息 |

下一步在可运行 PostgreSQL 的环境中验证迁移，再把解码器接到 MQTT 接入链路并补前端骨架；硬件到位后启动串口与 OTA 空间验证。
