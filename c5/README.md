# ESP32-C5 物联网模块固件

当前版本：0.7.0-dev；硬件：V0.14.4、ESP32-C5-WROOM-1U-N8R8；开发基线：ESP-IDF 5.5.1。

后端协议已确定为MQTT；用户正在整理接入文档，本轮暂缓后端集成，优先板内控制。灯的已确认规则、实现状态和完整待办见[板内控制清单](../docs/c5-board-control-requirements-v0.14.4.md)。

## 当前可用功能

- 板级安全初始化：RS485 DE保持低、LTE开关机/复位驱动保持未触发、8颗低有效LED默认熄灭。
- USB Serial/JTAG日志与交互控制台；现场UART0重映射到GPIO23/24，9600、8N1。
- 协议1.8外层编码/解析：AC AC包头、大端长度、16位累加和；支持半包、连包、噪声、部分帧超时、最大4096字节帧。设备相关N字节不作机型解释。
- 单在途请求、自动B2查询、显式启停/暂停/继续及参数发送；C1～C5事件本地处理和应答。面板事件发生后，不用较早请求的回复覆盖新状态。
- 新鲜运行余时正常每10秒保存到独立128KiB NVS分区；关键变化250ms合并、至少间隔2秒，重复事件节流，失败5秒后用最新值重试；双槽/CRC格式不变，历史不会成为当前值或触发控制。
- 主板通信与状态新鲜度独立诊断：合法匹配回复/事件维护接触状态，B2与计时事件维护实际运行观测；过期标记stale，不冒充当前事实或重复写旧值。
- 存储初始化/写入错误、损坏槽、提交时刻、落后/待写/重试和合并计数可查询。细节和验收见[运行健康说明](../docs/c5-runtime-health.md)。
- 5个关键任务推进监督与TWDT复位保护、RTC故障上下文；无卡/断网/主板无回复不等同任务卡死。
- 现场UART帧/奇偶/BREAK/溢出/读取错误、队列压力采样与保守恢复；不自动重发设备控制。
- B1/B3/C5原始N字节RAM缓存、长度/格式/CRC/revision与原子快照；保护新C5不被旧B3覆盖。实现及首板验收见[任务/UART/缓存说明](../docs/c5-task-uart-cache.md)。
- 最近64条故障/状态变化RAM记录、序号分页与覆盖缺口诊断；不保存凭据/原始参数，不增加Flash写入。
- 电脑主板模拟器：正常/故障回复、计时/面板事件、变长参数、C5与旧B3交错；工具和接线见[本地诊断与首板模拟器](../docs/c5-local-diagnostics-and-bench.md)。
- Wi-Fi STA双频自动选择（2.4/5GHz）、连接/IP状态、断线重连与20秒连接超时；通过信道报告实际频段。
- ML307R独立UART1 AT探测、一次受控开机脉冲、CPIN查询和SIM未知/缺卡/就绪/锁卡分类；两次连续明确缺卡回复才确认无卡。
- 开机45秒检测窗口结束后，明确无卡且Wi-Fi未取得IPv4才自动进入180秒SmartConfig。初始Wi-Fi成功后关闭自动配网判定，运行中掉线不自动配网；未知/锁卡保持诊断。
- 新配网信息在RAM中试连，确认目标AP关联并取得IPv4后才保存到独立wifi_profile命名空间；失败恢复原配置、不清除NVS，不记录Wi-Fi密码日志。
- 4G侧读取实际型号/固件、CSQ、CEREG、附着、CID 1激活状态及IPv4；只对确认ML307R的模组启用数据操作，附着/激活失败至少间隔30秒重试。
- ML307R AT TCP接口：流缓存接收、HEX编解码、256字节分块、异步连接结果、会话号隔离；不重发结果不明确的写入。
- 单连接应用传输适配器：新连接优先Wi-Fi，连接失败后可切换4G；30秒后允许新连接重试Wi-Fi。已建立的TCP不跨链路迁移。
- net probe/net echo台架诊断和电脑回显工具；仅在显式指定端点后连接，不自动转发TTL或接入任何公网示例服务器。
- 独立LED管理任务：绿灯网络就绪、蓝灯真实MQTT会话，Wi-Fi橙灯配网；TX/RX按现场UART字节活动触发，RX错误帧也显示，TX覆盖长帧提交/排队时间。
- 非阻塞逐灯测试、5秒单灯临时覆盖、自动恢复，以及灯状态/字节数诊断。当前MQTT客户端未接入，自动显示下蓝灯保持熄灭。

本版4G传输与选路为**普通TCP台架适配器**，尚未完成TLS证书校验、云端认证/MQTT、独立周期性网络健康检查、小程序发送端/正式引导、正式设备身份/二维码和OTA下载/签名/回滚。取得IPv4/PDP地址、甚至目标TCP连接成功，均不等于业务在线。双OTA分区仅预留。C7当前返回不支持，B5/C6没有控制台入口，C5仅确认RAM缓存更新，尚未持久化和上云。正式云端控制持久去重另行实现，当前控制台请求不是云端命令实现。

## VS Code使用

保持以本目录为工作区。已有settings.json保持原状，新增任务位于.vscode/tasks.json。

1. 按Ctrl+Shift+B执行默认任务 **C5: Build**。
2. “终端→运行任务→C5: Host protocol tests”执行相同C源代码的本地协议测试。
3. 板卡正常供电、USB接线与端口确认后，可主动运行 **C5: Flash and monitor**，输入实际COM端口。

任务调用tools/idf.ps1，显式使用已安装的IDF专属Python 3.11，避免系统Conda Python 3.13干扰；禁用本机曾卡住的ccache。Git目录信任例外仅在构建进程中生效，不改全局Git配置。默认路径为D:\Espressif，可用脚本的-IdfRoot和-ToolsRoot参数适配同版安装位置。

终端等价命令：

```powershell
.\tools\idf.ps1 build
.\tools\idf.ps1 -p COM5 flash monitor
.\tools\test-host.ps1
```

用实际端口替换COM5。IDF监视器用Ctrl+]退出。只连接3.3V USB-TTL适配器不能代替J6的原生USB下载连接。

## 上电与TTL接线

J3：1=VIN_IN主电源、2=模块TX、3=模块RX、4=GND。TX接主板RX，RX接主板TX，共地。TTL逻辑为3.3V，VIN_IN不是逻辑电源/对外供电输出。一次只连接一组现场接口。

J6：1=GND、2=USB D+、3=USB D−、4=EN、5=BOOT(GPIO28)。J6不提供USB 5V供电，EN不能接5V；整板仍从主电源入口供电。LTE开关机和复位驱动经Q1反相：本版先探测AT；无应答才将GPIO6拉高2500ms触发一次模组端低脉冲，不自动触发RESET。首次烧录前须核对装配与开关机时序。

固件按8MB Flash、Quad PSRAM 40MHz构建。为兼容无PSRAM开发板，允许PSRAM未找到时继续诊断；启动日志会明确报告容量与N8R8预期差异，不代表无PSRAM通过硬件验收。

## USB控制台

正常启动后出现c5>提示符。上电只周期发送B2读取状态，不自动发送A1等控制指令。

| 命令 | 用途 |
|---|---|
| help | 查看命令 |
| status | 查看主板通信在线/失联与观测新鲜度、存储健康/待写/重试、历史快照、灯/网络及UART统计 |
| net provision | 显式开始SmartConfig，会中断当前Wi-Fi；超时恢复原配置 |
| net probe auto host port | 后台测试指定端点TCP连接；auto可替换为wifi或lte |
| net echo auto host port 00ACAC0D0A4F4B | 向自己的TCP回显服务器发送显式测试字节并比较返回；最多256字节 |
| device state | B2查询 |
| device type | B1查询，内部数据按N字节处理 |
| device params | B3查询 |
| device start 60 | 显式发送A1，启动60秒 |
| device pause | A3暂停 |
| device resume | A4开始/继续 |
| device stop | A2停止，保留主板返回的剩余时间 |
| device set 020503040101 | B4原样发送参数十六进制；控制台最多256字节，核心帧载荷上限4089字节 |
| led 0 on / led 0 off | 对0号灯临时强制亮/灭5秒，索引0～7；到期自动恢复 |
| led test | 按0～7顺序逐灯亮，每颗250ms，2秒后恢复；不发设备控制命令 |
| led auto | 立即恢复自动状态显示 |
| cache info / cache params | 只读RAM缓存元数据与前64字节HEX，不发串口命令 |
| cache params 64 256 | 从偏移64导出最多256字节，分段读取需核对revision/CRC |
| events / events 16 16 | 从序号之后分页导出只读RAM故障记录，跟随next并核对boot/gap |

“queued”仅表示排入发送队列，不表示主板已执行。无主板时timeout增长属于预期，随后BOARD_CONTACT显示offline；BOARD_STATE单独标记unknown/fresh/stale。HISTORY仅为历史。控制台仅用于台架，未实现云端任务有效期/掉电幂等保证，不作为生产远控入口。

## 首轮配网

使用[乐鑫Android ESPTouch 2.3.2或更新版本](https://github.com/EspressifApp/EsptouchForAndroid/releases/tag/v2.3.2)，该版本已明确加入C5的5GHz配网支持。App内选择**ESPTouch/v1**，与固件SC_TYPE_ESPTOUCH保持一致；手机连接目标Wi-Fi。首轮将5GHz与2.4GHz设成不同SSID便于验收，再测试双频同名。

无SIM、无可用旧Wi-Fi时，上电约45秒后灯闪烁并进入180秒接收窗口；也可通过net provision手动触发。小程序名称、二维码与跳转信息尚未配置，本版用USB提示和LED显示状态。详细时序、边界和首板用例见[网络联调说明](../docs/c5-network-bringup.md)。

menuconfig中可调整AT波特率（暂定115200）、开机检测窗口、SmartConfig窗口和部署国家码（暂定CN）。本版台架凭据保存在普通NVS，量产凭据保护尚未启用。

## 4G与应用选路

按[4G联调说明](../docs/c5-lte-bringup.md)核对SIM、实际ML307R型号、注册和CID 1。APN默认留空，使用运营商/模组已有上下文；明确设置APN后须匹配，若旧CID仍激活且不匹配会保持不可用，不强行断开最后一条承载。包含ML307C字样的资料包中通用AT/TCP文档适用于R系列，但其中ML307C固件不能作为本板固件直接刷写。

tools/echo-server.py提供电脑端台架回显，默认仅监听127.0.0.1。Wi-Fi实板测试需指定电脑局域网地址；4G测试端点须能从蜂窝网络访问，电脑内网地址通常不可直达。net probe只连接，net echo才发送输入的测试字节，均在独立任务中执行。TCP结果只用于当前端点和新连接选路，不触发配网、不清配置、不重放设备控制。

## 桌面测试

tests/test_core.c直接编译生产用module_core C源代码，golden_vectors.h来自用户协议18条Demo，来源SHA-256和长度核算见[协议证据](../docs/iot-module-uart-v1.8-evidence.json)。24491项检查覆盖原协议/记录/网络/灯/运行健康/任务监督/UART/缓存，以及本地故障环的覆盖、分页、缺口、饱和与快照。tools/bench.ps1 -SelfTest另通过25项模拟器自测，不打开真实串口。电脑回显工具此前通过2073字节二进制往返冒烟检查。实际任务看门狗复位、RTC保留、并发互斥、ESP-IDF调度、NVS真实故障/掉电、AT时序、无线收发和GPIO仍须实板验证。

本机便携TinyCC已放在被忽略的build-host/tcc目录。其他机器可用tools/test-host.ps1 -Compiler指定兼容GCC/TinyCC；本地工具不进入固件和版本库。TinyCC官方归档：

- [官方项目](https://bellard.org/tcc/)
- [0.9.27 Windows x64归档](https://download.savannah.gnu.org/releases/tinycc/tcc-0.9.27-win64-bin.zip)
- 本次下载SHA-256：34a721949a2583fdff725312da092fa0f5f1f284b702e6f811c6954714faabb2。

## 首板验收与已知限制

当前验证为主机测试与C5交叉编译；尚未烧录或测量实板。板到后依次验证电源、USB、启动容量、灯、TTL真实收发、主板面板事件、10秒记录和掉电恢复。

协议没有串口事务ID，超时后的静默排空和事件版本保护只能降低迟到回复风险，不能完全消除同命令迟到歧义。长帧按9600波特率计入发送耗时；串口中断、Flash掉电原子性和磨损仍要真机验证。新版本Flash分区已经划分，后续更改分区前须保留有效数据，不应为排错自动擦除运行记录。

VS Code新增C5: Bench tool self-tests与C5: Mainboard simulator；后者需手动输入USB转3.3V TTL适配器COM，不能填ESP USB控制台COM。模拟器可在c5目录用tools/bench.ps1 -Port COM12显式启动，COM12仅为示例。

下一阶段补可信校时/B5编码与有效性、工厂验收用例与报告；参数持久化、完整C5事件补传和量产维护入口仍待开发。后端MQTT接入等用户文档；板到后先按[模拟器联调顺序](../docs/c5-local-diagnostics-and-bench.md)验证，再做看门狗、NVS/真实掉电、无线与电气测试。
