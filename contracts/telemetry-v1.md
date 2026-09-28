# 遥测二进制协议 v1（候选）

本契约用于模拟器、固件、Java 接入模块共享实现。所有多字节整数采用网络字节序；Modbus 寄存器字节序只用于 DTU 解码，不影响本帧。

| 偏移 | 长度 | 字段 |
|---:|---:|---|
| 0 | 2 | magic = `44 54`（DT） |
| 2 | 1 | version = 1 |
| 3 | 1 | messageType = 1（telemetry） |
| 4 | 4 | payloadLength，不含 47 字节固定头 |
| 8 | 4 | configRevision，必须大于零 |
| 12 | 16 | bootId，随机生成的原始 16 字节 |
| 28 | 8 | sequence，启动期间递增，从 1 开始；v1 有效范围 1～2^63-1，兼容数据库有符号 bigint |
| 36 | 8 | sampleTimeMs，UTC 毫秒；时间不可信时为 0 |
| 44 | 1 | flags，bit0=补传，bit1=时间可信，其余位必须为 0 |
| 45 | 2 | pointCount，1～128 |
| 47 | 变长 | 重复的数据点 |

每个数据点按顺序编码：`pointCode:uint16`、`rawType:uint8`、`quality:uint8`、`sampleOffsetMs:int32`、`valueLength:uint16`、`rawValue:bytes`，固定部分 10 字节。`sampleOffsetMs` 相对于公共 sampleTimeMs。时间不可信时 offset 必须为 0。

| rawType | 值 | 长度 |
|---|---:|---:|
| UINT16 | 1 | 2 |
| INT16 | 2 | 2 |
| UINT32 | 3 | 4 |
| INT32 | 4 | 4 |
| FLOAT32 | 5 | 4，IEEE 754，禁止 NaN/Infinity |
| BOOL | 6 | 1，仅允许 0 或 1 |

quality：0=GOOD，1=READ_TIMEOUT，2=MODBUS_ERROR，3=INVALID_VALUE。GOOD 要求数据长度与类型匹配；异常质量的 valueLength 必须为 0。失败不上传假值。单帧总长最多 4096 字节，pointCode 必须大于零、批内唯一，payloadLength 必须精确匹配剩余字节。

服务端通过已认证 MQTT 网关身份与 `(gatewayId, bootId, sequence)` 去重；绝不信任载荷指定租户。configRevision 必须能定位该网关不可变配置快照。未知版本、类型、质量、非法长度、重复点、未发布 revision 直接拒绝并记录诊断；对合法旧 revision 按旧配置转换。

这里没有对 MQTT TLS 流量叠加 CRC；传输层损坏由 TLS 处理。应用层持久接收 ACK 独立于 MQTT PUBACK。ACK 需要确认持久接收完成后才能发，固件据此清理离线缓存。

`telemetry_v1.py` 与 `test_telemetry_v1.py` 是编码参考实现；`TelemetryV1.java` 已通过同一 golden vector。C 固件实现和更多异常向量通过后，才能把本草案标为冻结。
