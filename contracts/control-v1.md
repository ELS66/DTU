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
  "contentHash": "adb8caea5ba67a5aedf21ce6ef9795170c4397c14d505f0be38fd1ef7c21deb0",
  "serial": {"port": "RS485", "baudRate": 9600, "dataBits": 8, "stopBits": 1, "parity": "NONE"},
  "points": [{
    "pointCode": 1, "slaveId": 1,
    "read": {"function": 3, "address": 0, "count": 1, "intervalMs": 1000},
    "write": null, "rawType": "INT16", "byteOrder": "AB"
  }]
}
```

`contentHash` 只覆盖执行配置 `serial` 和 `points`，不包括外层 `protocolVersion`、`releaseId`、`revision`、`expiresAt` 或 `contentHash` 本身。哈希输入是 UTF-8、无空格的 JSON，字段顺序固定为：顶层 `schemaVersion`、`serial`、`points`；`serial` 内为 `port`、`baudRate`、`dataBits`、`stopBits`、`parity`；每个点为 `pointCode`、`slaveId`、`read`、`write`、`rawType`、`byteOrder`；`read` 内为 `function`、`address`、`count`、`intervalMs`；`write` 内为 `function`、`address`。`schemaVersion` 固定为整数 1，点先按 `pointCode` 升序排序；空映射编码为 JSON `null`。所有配置数值都是十进制整数，枚举都是本文规定的 ASCII 字符串；禁止额外字段。执行配置的规范化 UTF-8 字节不得超过 32768 字节。SHA-256 以 64 个小写十六进制字符表示。

共享向量见 [`config-v1-vector.json`](config-v1-vector.json)，Python 参考实现为 [`config_v1.py`](config_v1.py)，Node 实现为 `backend/src/protocol/config-release.ts`。上例 hash 与所示执行配置匹配；`expiresAt` 只是示例时间，实际发布时必须设置有效截止时间。

配置验证限制：`revision` 为 1～4294967295，与遥测帧的 `configRevision` 一致；点数为 1～128，`pointCode` 唯一且为 1～65535，`slaveId` 为 1～247；串口限定 RS485/RS232/TTL、8 数据位、1/2 停止位、NONE/EVEN/ODD 校验，波特率 1200～115200。`read` 与 `write` 至少有一个非空。BOOL 读取只允许功能码 1/2、写入功能码 5；16 位数值读取只允许 3/4、写入 6；32 位数值读取只允许 3/4、写入 16。读取寄存器数必须与类型宽度匹配，地址及寄存器范围不能越过 65535；采集间隔为 100～3600000 毫秒。16 位和 BOOL 字节序固定 `AB`；32 位允许 `ABCD`、`BADC`、`CDAB`、`DCBA`。这是一版明确可执行的子集，其他 Modbus 功能码和位域映射需要新契约版本。

服务器保存完整快照，DTU 仅看到执行所需字段。DTU 还须校验过期时间、单调 revision、串口能力和调度负载，在持久保存完成后原子切换。收到相同 releaseId 时仅返回已有结果，不重复应用。

上行 `config/reply`：`protocolVersion`、`releaseId`、`revision`、`status`（RECEIVED、APPLIED、REJECTED）、`errorCode`、`appliedRevision`。`appliedRevision` 为 0～4294967295；当 status 为 APPLIED 时，它必须等于本条 reply 的 revision。REJECTED 必须给出 `errorCode`，其余状态必须为 JSON `null`。只有 APPLIED 更新云端 appliedRevision。云端应使用实时查询或重试同步恢复丢失的 reply。

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

`configRevision` 为 1～4294967295，`pointCode` 为 1～65535。`rawValue` 与 `rawType` 匹配：BOOL 使用 JSON 布尔值；UINT16、INT16、UINT32、INT32 使用其二进制范围内的整数；FLOAT32 使用可表示的有限 JSON 数值，设备按 IEEE 754 float32 舍入。结构校验不代替执行校验：到期时间、当前 applied revision、映射、写权限和命令去重必须由设备执行前再次确认。

上行 `command/reply`：`protocolVersion`、`commandId`、`configRevision`、`status`、`errorCode`、`observedRawValue`、`observedAt`。状态为 RECEIVED、EXECUTING、WRITE_ACKED、VERIFIED、FAILED、REJECTED。只有 VERIFIED 必须同时给出非空 `observedRawValue` 和 UTC 毫秒 `observedAt`；其他状态两者都必须为 JSON `null`。FAILED、REJECTED 必须给出 `errorCode`，其余状态必须为 `null`。服务端按 commandId 找到原命令，再核对回读类型、设备归属与配置版本；不能仅靠 reply 声称 VERIFIED。W 点可结束于 WRITE_ACKED，不假装已验证状态。MQTT PUBACK 不是物理设备执行成功。

服务端公开的结果额外包含 UNCONFIRMED、EXPIRED。超时任务不能覆盖已经记录的晚到执行事实；用户界面可提示“结果未确认，请查看设备当前状态”。

## 遥测持久接收确认

上行 `telemetry` 使用二进制协议。服务器将批次写入 inbox 并提交后，回传 `telemetry/ack` JSON：`protocolVersion`、`bootId`、`sequence`、`status`（STORED 或 REJECTED）、`errorCode`。`bootId` 是 16 字节原值的 32 字符小写十六进制；`sequence` 是范围 1～2^63-1 的**十进制字符串**，不能用 JSON number，避免超过 JavaScript 安全整数后丢精度。STORED 的 `errorCode` 必须是 `null`，REJECTED 必须给出错误码。重复的同一批次返回 STORED。DTU 只有收到 STORED 才从离线队列释放该批次。若报文头损坏到无法可信读取 bootId/sequence，服务端记录诊断但不构造猜测身份的 ACK。

`command/set`、`command/reply`、`config/reply`、`telemetry/ack` 各自的 UTF-8 JSON 载荷上限为 1024 字节，禁止重复字段和额外字段。错误码为 1～64 字符的大写 ASCII，首字符为字母，后续只允许字母、数字和下划线。共享样例与 Python/Node 校验器见 [`control-v1-vector.json`](control-v1-vector.json)、[`control_v1.py`](control_v1.py) 和 `backend/src/protocol/control-messages.ts`。最大重投递时长、超时和退避仍待定义；C 固件实现和 JSON Schema 尚未完成，因此整个控制契约仍为草案。
