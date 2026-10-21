# ESP32-C5 本地故障记录与首板串口模拟器

日期：2026-10-20；固件0.7.0-dev；硬件V0.14.4；ESP-IDF 5.5.1。源码、共享核心测试、电脑工具自测和交叉编译完成，尚未烧录、打开任何真实COM端口或验证实物时序。软件验证记录见[本轮证据](c5-events-bench-evidence.json)。

## 1. 本地故障与状态记录

新增固定64条的RAM环形记录，无独立任务、无动态入队、无Flash写入。每条只保存本次启动内的递增序号、启动后毫秒、事件码和两个32位数值。记录满时覆盖最旧条目，报告累计覆盖数；序号到UINT64_MAX后拒绝新增而不回绕，拒绝计数饱和。并发写入由独立短临界区保护，读取一次最多复制16条后释放锁，再输出USB文本。

记录的是变化和故障，不是原始串口字节流或完整业务事件队列：

| 事件码 | 名称与字段 |
|---|---|
| 1 / 2 | BOOT：detail=SDK复位原因；PREVIOUS_STALL：detail=上次RTC任务故障位图 |
| 10 / 11 | BOARD_OFFLINE / BOARD_RECOVERED；恢复detail=是否匹配请求回复 |
| 12 | BOARD_STATE：detail高8位为来源命令、低8位为状态，value为该次观测剩余秒 |
| 20 / 21 | UART_FAULT：detail为错误标志；UART_RECOVERED。连续同一故障阶段只记首次，细分计数仍在status |
| 22 / 23 / 24 | CACHE_FAILURE：命令与长度；STALE_PARAM_REPLY：命令；UART_TX_FAILURE：value为请求发送长度 |
| 30 / 31 | STORAGE_INIT_FAILURE：detail为错误码；STORAGE_INVALID_SLOT：detail为槽号、value为读取错误码，0表示读取成功但记录解码失败 |
| 32 / 33 / 34 | STORAGE_WRITE_FAILURE：错误码变化时记录；STORAGE_RECOVERED：detail为前次错误；STORAGE_EXHAUSTED：记录序号耗尽 |
| 40 / 41 | WIFI_READY / WIFI_DOWN：detail最近断线原因，value当前信道。网络就绪不等于MQTT在线 |
| 42 / 43 | PROVISION_START / PROVISION_END：detail为当时是否仍有候选配置 |
| 44 / 45 / 46 | NETWORK_DROPS累计事件丢弃数；NETWORK_ERROR错误码；WIFI_SAVE_ERROR配置保存错误变化，0表示恢复 |
| 50 / 51 / 52 / 53 | MODEM_SIM / MODEM_REGISTRATION：detail新值、value旧值；MODEM_DATA / MODEM_AT：detail为新布尔值 |
| 60 / 61 | TASK_STALL：detail为任务故障位图；TASK_DISABLED：detail为未创建任务索引 |
| 70 | COMPONENT_FAILURE：detail为组件索引0系统NVS/1蜂窝/2Wi-Fi/3uplink，value为初始化错误码 |

正常B2轮询、倒计时逐秒变化、每10秒成功快照均不逐条记录；首次有效运行观测、工作状态改变才记BOARD_STATE。状态新鲜度仍由status实时推导，未单独为每次fresh/stale变化建立事件。保存失败的相同错误重试不会每次占一条；重复故障与高频不同状态仍可能快速覆盖64条，这不是完整审计日志。

事件字段不接受任意字符串，不保存SSID、密码、APN、服务器地址、设备身份或原始机型参数。时间是ESP本次启动的单调毫秒，入环时若其他任务抢先提交则钳位到最近时间，序号表示入环顺序，不是UTC或精确硬件中断顺序。

事件环在复位/断电后清空。上次任务故障仅沿用0.6.0-dev已有RTC上下文，在下一次启动可生成PREVIOUS_STALL；它不是跨断电日志，不能保证CPU完全卡死时有位图。原历史余时记录、分区和36字节格式不变。

## 2. 只读分页导出

在ESP USB控制台执行：

~~~text
status
events
events 16 16
~~~

events语法为events [after_sequence [1..16]]，默认after=0、limit=16，从当前保留范围中返回大于游标的记录。

- EVENTS头包含boot、capacity、retained、oldest、latest、overwritten、rejected、gap和cursor_ahead。
- EVENT行包含seq、at、code、name、detail、value，后两项以8位HEX打印。
- EVENTS_END给出count和next。下一页用next作为after，同一批导出必须核对boot相同。
- gap=1说明游标后的部分记录已覆盖；它是明确缺口，不会默默当成完整历史。
- cursor_ahead=1说明传入序号比当前最新值大，命令返回失败；核对是否模块重启或使用了其他模块的游标。
- 每页是完整副本，分页期间新事件可能覆盖尚未读出的旧事件，下一页仍会报告gap。没有读后删除、清空、复位或Flash擦除命令。

status只显示环摘要，不自动输出所有记录。长时间运行需要电脑及时分批保存USB输出；本轮未提供自动采集ESP控制台的客户端。

## 3. 首板连接与启动模拟器

模拟器代替设备主板。使用时断开真实主板TTL，仅连接一个USB转3.3V TTL适配器：

| 适配器 | PCB现场TTL |
|---|---|
| TX | RX，ESP GPIO24 |
| RX | TX，ESP GPIO23 |
| GND | GND |

通过V0.14.4规定的VIN供电，适配器只接TX/RX/GND；J6 USB调试接口没有USB 5V输入。ESP的USB控制台与USB转TTL适配器是不同COM端口，前者用于status/device/events，后者给模拟器使用。不能把RS232电平接口直接当成TTL。

VS Code已增加：

- C5: Bench tool self-tests：只运行内存/虚拟时钟测试，不打开COM。
- C5: Mainboard simulator：提示输入USB转TTL适配器COM。
- 原C5: Build和C5: Flash and monitor保持原用途，烧录仍由操作者明确触发。

也可在c5目录运行，COM12仅为示例：

~~~powershell
./tools/bench.ps1 -SelfTest
./tools/bench.ps1 -Port COM12
./tools/bench.ps1 -Port COM12 --state running --remaining 120 --params-size 4088
./tools/bench.ps1 -Port COM12 --help
~~~

使用本机固定IDF Python和pyserial 3.5；其他电脑可用-Python指定已安装pyserial的Python。串口固定9600 8N1，DTR/RTS设为false后才打开指定端口，不扫描或自动选择端口。脚本默认模拟空闲且余时0；--state/--remaining可以模拟主板在模块启动前已运行或暂停。

脚本只驱动所选TTL连接，不操作ESP控制台或真实设备的业务界面。Ctrl+C或quit停止，不改变模块配置。断电、电平、真实帧/奇偶错误、看门狗卡死和电源恢复仍需专用实物测试。

## 4. 模拟范围和操作

实现独立协议编解码并核对用户表格18条Demo。模拟A1/A2/A3/A4、B1/B2/B3/B4、C1～C5事件与模块ACK；B5/C6返回不支持，不编造可信时间或正式身份。暂停冻结余时，停止保留余时，运行自然到0时发一次C1；这是台架模型，不能代替目标主板业务验收。

B1去状态码后的info、B3参数均为原始N字节；初始B3最多4088字节，C5最多4089字节。若C5/B4设置了4089字节参数，B3无法再容纳状态码，模拟器明确返回02，不截断参数。

在模拟器窗口输入：

| 命令 | 用途 |
|---|---|
| help / status / quit | 查看帮助、计数/状态、退出 |
| panel start 120 | 面板启动，发C2 |
| panel pause / resume / stop / expire | 发C3/C2/C4/C1并改变模拟主板状态 |
| panel params 00ACAC55 | 更新模拟参数并发C5；保留二进制00和AC AC |
| panel params - | 空N字节C5 |
| panel params-size 4089 | 生成最长C5 |
| race-params 00ACAC55 | 下一次成功B3查询时先发新C5，再发旧B3回复，仅触发一次 |
| race-params-size 32 | 用生成的32字节新值做同样交错 |
| burst 100 20 | 最多1000次面板状态事件，间隔20～5000ms；用于队列/灯/记录节流联调 |

race场景建议先用短参数，避免两个长帧总耗时另外触发请求超时。在模拟器arm后，在ESP窗口执行device params，再看cache params，最终必须是新C5内容，stale_param_reply应增加。脚本不会把收到的C5 ACK再次应答。

故障模式：

| 模式 | 行为 |
|---|---|
| mode normal | 正常回复 |
| mode silent | 丢弃所有模拟发送，仍推进模拟主板内部计时 |
| mode bad-checksum | 发送帧最后一个校验字节翻转 |
| mode fragmented | 分片发送一帧，默认64字节/片、片间1ms；帧间不交织，可用--chunk-size/--gap-ms调整 |
| mode truncated | 每帧去掉最后2个校验字节 |
| mode late | 默认延迟1500ms，可用--late-ms调整；用于迟到与同命令歧义观察 |

模式在帧入队时生效，切换模式会丢弃尚未发出的排队内容；已写入串口驱动的字节无法撤回。发送队列最多128帧，满后丢弃并计dropped，命令队列16项。分片增加的间隔会增加线速总耗时，过长间隔/大帧可合理超时，不应当成固件故障。模块协议没有事务ID，迟到的同命令回复仍存在歧义；不能据此工具宣称已彻底消除。

可加--duration限制运行秒数，--trace指定一个尚不存在的JSONL文件。trace只写收到的有效帧命令/长度和发送分片长度/模式，不记录参数正文；已有文件拒绝覆盖。它不是完整串口抓包，也不证明驱动真正发完或对端已收到。

## 5. 首板操作顺序

1. 正常模拟空闲，ESP执行status：等待B2建立fresh；核对TX/RX灯和info/params显式读取。
2. mode silent保持超过8秒，ESP应出现状态过期、主板失联；events可见BOARD_OFFLINE，不应自动启停或恢复历史余时。
3. mode normal恢复后核对BOARD_RECOVERED，实际状态重新以主板查询为准。
4. 分别bad-checksum、truncated和fragmented；检查错误/部分帧计数、RX灯、正常模式恢复，不将坏校验当合法状态。
5. 执行race-params和不同N长度，分段cache导出核对长度、revision和CRC；实测4096字节长回复。
6. burst 100 20并同时读取events/status，检查日志有界、缺口可见、串口ACK和10秒快照节流。无需先进行极限压力。
7. 在专用测试构建中分别阻塞任务/注入NVS错误，核对TASK_STALL、RTC恢复上下文、存储失败/恢复；这些不是本模拟器的能力。
8. 单独验证模块与主板重启、真实突然断电、Wi-Fi/4G并发及24h稳定性，保留USB输出和测试配置。

## 6. 软件验证与剩余事项

共享生产C累计24491项检查通过，新增环为空/边界、1000次写入与64条保留、顺序分页、游标缺口/超前、页副本不受后续覆盖影响、时间钳位和序号/计数饱和。模拟器25项自测通过，覆盖18条原Demo及所有切分点、二进制/长帧、倒计时与控制、故障模式、有界排队、部分写入、ACK不循环、C5与旧B3交错。VS Code任务JSON和工具帮助入口已检查。

ESP-IDF编译通过，当前镜像998960字节，3MiB应用槽约68%空闲。自测使用内存传输和虚拟时钟，不打开串口；不能替代驱动、GPIO、USB桥、实物主板与电源测试。日志的实际并发开销、系统调度和硬件故障仍待首板。

后续继续可信校时/B5的编码与时间有效性、工厂验收报告与测试用例；参数持久化、C5事件可靠保存/补传、量产维护入口另行设计。MQTT/TLS接入继续等待用户文档，未改变灯语义、设备自动控制策略、分区或余时历史格式。
