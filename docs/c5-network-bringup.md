# C5 0.2.0-dev 网络与配网联调说明

> 本文保留0.2.0-dev的配网基线。后续已加入AT TCP/新连接选路，并在0.4.0-dev按用户确认更新灯语义。旧灯表、LTE_pending和“4G传输未实现”等历史描述以[板内控制清单](c5-board-control-requirements-v0.14.4.md)、[4G联调说明](c5-lte-bringup.md)及[开发进度](c5-firmware-progress.md)为准；开机配网条件继续沿用。

日期：2026-10-20。硬件V0.14.4，ESP-IDF 5.5.1。本文记录开发参数和验收方法，不增加用户未确认的产品要求。

## 本轮实现边界

已接入ESP-IDF Wi-Fi/SmartConfig驱动和ML307R UART/AT代码；所有源码交叉编译通过。尚未连接实物，不能视为5GHz配网或ML307R型号兼容性实测通过。4G数据适配器、默认路由切换、基础互联网健康检查和云端连接尚未实现；SIM READY仅表示卡可用，Wi-Fi ready仅表示取得IPv4。

TTL与10秒余时快照使用独立任务，不等待网络初始化成功；网络异常不会回写主板历史余时或启动设备。

## 开机和配网

1. 并行启动TTL、余时记录、Wi-Fi与AT检测。Wi-Fi尝试已保存配置，STA启动后显式设置WIFI_BAND_MODE_AUTO，覆盖2.4GHz与5GHz。
2. 开机检测窗口暂定45秒。窗口内Wi-Fi取得IPv4即关闭本次开机自动配网判定；之后掉线只重连。
3. 窗口结束时使用15秒内的新SIM观测。只有连续两次CPIN查询明确返回无卡，且Wi-Fi未取得IPv4，才进入SmartConfig。SIM未知、AT超时、通用ERROR、锁卡、SIM故障都不按缺卡处理。
4. 有卡但Wi-Fi不可用时，当前报告LTE_pending；4G数据链路仍待实现。检测结束时SIM仍未知也关闭本次自动判定，后续状态变化不会在运行中突然启动配网；可用USB的net provision主动重试。
5. 配网前停止旧Wi-Fi并重新启动到无关联状态，避免旧连接的IP事件误判新配置已验证。接收新信息后仅写RAM；核对关联AP的SSID/BSSID并取得IPv4后，才写wifi_profile/credentials。
6. SmartConfig窗口暂定180秒。正常取得IPv4后等待App ACK完成；未收到ACK时最多等待至窗口结束，保留已经验证的连接。失败或网络事件队列丢失时取消候选配置并恢复原配置，不自动循环配网、不擦除NVS。写Flash失败单独报告并每5秒重试，RAM中保留原配置备份。

每次连接尝试最多等待20秒，包括关联成功但迟迟没有IPv4的情况；失败后间隔5秒重试。配网窗口、开机窗口、AT波特率和国家码均在menuconfig的V0.14.4 IoT module菜单中调整，目前为台架参数，量产值由实测固定。

首轮发送端使用[乐鑫Android ESPTouch 2.3.2或更新版](https://github.com/EspressifApp/EsptouchForAndroid/releases/tag/v2.3.2)，该版发布记录明确加入C5的5GHz支持。App选择ESPTouch/v1；固件使用SC_TYPE_ESPTOUCH，暂未启用ESPTouch V2。手机连接目标SSID，首测将两个频段命名分开；是否实际连接5GHz以固件channel与路由器终端信息核对。默认国家码CN，其他部署地区须调整对应配置。

正式小程序及设备二维码尚未提供，本版只用USB日志和指示灯提示。没有编造小程序链接或二维码，也没有实现手机端发送界面。

## ML307R 探测

- UART1：GPIO0 TX、GPIO1 RX，暂定115200 8N1，无硬件流控。板到后核对出厂AT固件与波特率。
- 上电等待750ms，先尝试三次AT；无应答才经Q1反相输出一次模组PWRKEY低脉冲，MCU GPIO6高2500ms。随后最多15次启动探测；以后仅探测，不重复开机脉冲，不触发RESET。
- AT恢复后发送ATE0、AT+CMEE=2，随后每5秒AT+CPIN?。不自动输入PIN/PUK，不改变SIM内容。
- +CPIN: READY后跟OK才确认就绪；明确PIN/PUK状态报告锁卡。无卡只接受CPIN事务中的+CME ERROR: 10或明确的SIM not inserted文本；普通ERROR、13/SIM故障、超时、未知文本、损坏/超长行均保持未知。
- 行解析支持回显、无关URC插入、CR/LF分割和逐字节输入；超时后排空500ms再发下一请求。AT本身没有事务ID，特别迟到回复仍需真机验证；不会据此宣称完全消除串口歧义。

SIM码值依据[3GPP TS 27.007 / ETSI TS 127 007 §8.3、§9.2](https://www.etsi.org/deliver/etsi_ts/127000_127099/127007/08.06.00_60/ts_127007v080600p.pdf)。开机时序依据[ML307R硬件手册 §3.9](https://atta.szlcsc.com/upload/public/pdf/source/20250926/81203B9442B53DF38E1C5C846E7C6057.pdf)。这是标准命令实现基线，ML307R实际AT版本对命令/错误码的兼容仍待到货验证；硬件手册不等于AT传输手册。

## 控制台和灯

status增加WIFI、PROVISION、MODEM三组状态，包括IPv4、信道、最近RSSI、断线原因、配网候选/保存状态、开机判定、SIM观测年龄、AT超时与UART错误。RSSI是最近一次取得IPv4时的值。net provision显式重开一次配网窗口，会中断原Wi-Fi。

| 灯索引 | 当前台架含义 |
|---|---|
| 0 ESP橙 | 未取得IP常亮；配网时与蓝灯交替闪烁 |
| 1 ESP绿 | Wi-Fi有IPv4；不表示云端在线 |
| 2 ESP蓝 | 配网闪烁 |
| 3 LTE橙 | AT未就绪或SIM未READY |
| 4 LTE绿 | 本版始终不亮，留给真实4G数据链路 |
| 5 LTE蓝 | AT与SIM均就绪；不代表已注册或已联网 |
| 6/7 | 现场TTL TX/RX短闪 |

## 首板验收清单（均待实测）

| 条件/操作 | 预期 |
|---|---|
| 无SIM、无旧Wi-Fi | 两次明确缺卡后，开机窗口结束进入SmartConfig |
| 无SIM、旧Wi-Fi可用 | 自动连接，后续关闭路由器只重连，不自动配网 |
| 有卡、Wi-Fi不可用 | 不自动配网；当前报告LTE_pending，不误报在线 |
| AT断开、锁卡、CME 13或未知错误 | SIM unknown/locked，不自动配网 |
| 2.4GHz独立SSID + ESPTouch v1 | 成功取得IPv4、保存、重启重连 |
| 5GHz独立SSID + ESPTouch v1 | 成功取得IPv4，channel>14且路由器核对为5GHz；保存、重启重连 |
| 双频同名SSID | 记录实际频段、不同手机/路由器兼容性和重连情况 |
| 原配置存在，手动配错密码或中断发送 | 超时恢复原配置；重启仍可用，不擦NVS |
| 配网成功、App ACK缺失 | 到窗口结束保留已验证Wi-Fi；核对App结果提示 |
| AP可关联但DHCP不响应 | 每次20秒超时后重连，不永远卡在连接中 |
| 配网事件压力/乱序、无线掉线 | 候选保存不会由旧连接或丢失的事件触发；无自动配网循环 |
| LTE已开机时只重启ESP | AT正常则不发开机脉冲；核对GPIO6/模组PWRKEY波形 |
| TTL主板持续工作，同时反复配网/断线 | TTL状态同步和10秒记录持续，模块不恢复历史余时到主板 |

主机测试覆盖共享C代码的AT行流、SIM确认、一次性开机决策、协议和记录编解码；无线驱动事件顺序、NVS掉电原子性、真实脉冲、电气与射频均不由这些测试替代。
