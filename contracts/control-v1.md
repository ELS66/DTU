# 配置与命令契约 v1 草案

两类低频控制消息采用 UTF-8 JSON。消息中的身份来自 MQTT 认证连接和 Topic；接收方不得以 JSON 里的设备 ID 改变目标。所有时间为 UTC 毫秒。JSON 用于便于首版硬件联调，后续如需换编码，使用新的协议版本。

## 配置发布

下行 `config/set`：

```json
{
  "protocolVersion": 1,
  "releaseId": "1b37a40b-1736-475f-bf57-0861fcb07c5a",
  "revision": 12,
  "expiresAt": 1780000100000,
  "contentHash": "64位十六进制SHA256",
  "serial": {"port": "RS485", "baudRate": 9600, "dataBits": 8, "stopBits": 1, "parity": "NONE"},
  "points": [{
    "pointCode": 1, "slaveId": 1,
    "read": {"function": 3, "address": 0, "count": 1, "intervalMs": 1000},
    "write": null, "rawType": "INT16", "byteOrder": "AB"
  }]
}
```

`contentHash` 是固定规范化序列化后的执行配置 SHA256，不包括外层 releaseId、expiresAt。规范化形式和测试向量需要在跨语言实现前锁定。服务器保存完整快照，DTU 仅看到执行所需字段。DTU 校验版本、单调 revision、hash、串口能力、点数及调度负载，在持久保存完成后原子切换。收到相同 releaseId 时仅返回已有结果，不重复应用。

上行 `config/reply`：`protocolVersion`、`releaseId`、`revision`、`status`（RECEIVED、APPLIED、REJECTED）、`errorCode`、`appliedRevision`。只有 APPLIED 更新云端 appliedRevision。云端应使用实时查询或重试同步恢复丢失的 reply。

## 绝对值控制

下行 `command/set`：

```json
{
  "protocolVersion": 1,
  "commandId": "0f23f2b2-03a8-482e-a697-cdc33438cfdb",
  "configRevision": 12,
  "expiresAt": 1780000100000,
  "pointCode": 2,
  "rawType": "INT16",
  "rawValue": 300
}
```

DTU 检查截止时间、已应用 revision、pointCode、类型与写权限。首次收到时保存 commandId 和处理阶段；重复到达时回复已有事实，不重新写 Modbus。命令持久去重记录的保留时间必须覆盖最大可能重投递时间；本地空间不足时停止接收新命令并报告错误。

上行 `command/reply`：`protocolVersion`、`commandId`、`configRevision`、`status`、`errorCode`、`observedRawValue`、`observedAt`。状态为 RECEIVED、EXECUTING、WRITE_ACKED、VERIFIED、FAILED、REJECTED。`observedRawValue` 仅在关联该命令的回读成功时出现。W 点可结束于 WRITE_ACKED，不假装已验证状态。MQTT PUBACK 不是物理设备执行成功。

服务端公开的结果额外包含 UNCONFIRMED、EXPIRED。超时任务不能覆盖已经记录的晚到执行事实；用户界面可提示“结果未确认，请查看设备当前状态”。

## 遥测持久接收确认

上行 `telemetry` 使用二进制协议。服务器将批次写入 inbox 并提交后，回传 `telemetry/ack` JSON：`protocolVersion`、`bootId`、`sequence`、`status`（STORED 或 REJECTED）、`errorCode`。重复的同一批次返回 STORED。DTU 只有收到 STORED 才从离线队列释放该批次。

以上消息都需要定义最大大小、超时和重试退避。JSON 字段名、类型和取值由后续 JSON Schema 与固件 golden vectors 锁定；本文件为第一阶段待验证契约。
