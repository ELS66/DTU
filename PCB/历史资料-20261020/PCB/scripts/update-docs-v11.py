from pathlib import Path
p=Path('PCB');f=p/'DTU主板硬件设计与API绘板规范.md';s=f.read_text(encoding='utf-8')
s=s.replace('版本：V0.6；更新：2026-10-10','版本：V0.11；更新：2026-10-12')
s=s.replace('本文件定义当前设计。V0.4 的优先级编码器、互锁、四通道 TTL 转换器和 USB-C 下载座方案已被替代，历史稿只供追溯。已在独立工程 DTU-C5-Air780EPT-HW-V0.1-library 完成九页原理图和 PCB 器件同步；全板布线尚未完成，当前文件不是投板批准。','本文件定义当前设计。V0.11 参考 RK_WB4G_V2 实测拓扑简化接口，采用 MAX3485、BL13232E 和三输入与门接收合并。九页原理图与 154 个 PCB 器件已同步；详细检查及剩余事项见 [V0.11 修改与验证记录](reports/V0.11接口修改与验证记录.md)。历史稿中的接口优先级和比较器选路已失效。')
a=s.index('三路 VIN 经各自');b=s.index('## 3. 电源和保护')
s=s[:a]+'''三路 VIN 经各自保险丝、防反接/反灌二极管合路，再进入公共电源保护。无需软件选择接口种类，按一次只连接一个接口设计。

FIELD_TX 共用发送源：连接 U6 的 DI、U7 的 DIN1 和 U8 的 TX 转换输入。RS232 和 TTL 发送输出在供电时跟随该信号；RS485 只在 MCU_485_DE 拉高时驱动总线。程序启动保持 DE=0，发送前拉高，等待 UART 最后停止位完全发出后拉低。此 DE 控制是半双工时序，不是接口配置。

FIELD_RX = 485_RX_RAW AND 232_RX_RAW AND TTL_RX_BUF。三个接收源各接 U12 独立输入，不将推挽输出直接并接。空闲均为高，任一路低使共享接收输出低。未连接接口的空闲状态由接收器和上拉定义。多个接口同时发数据会互相干扰，不属于当前使用方式。

### 2.1 现场接口器件

- U6 MAX3485ESA+（C1545222）：3.3V 半双工 RS485。1脚 RO，2脚 /RE 和 3脚 DE 并接 MCU_485_DE，4脚 DI 接 FIELD_TX；5脚地、6脚 A、7脚 B、8脚 3.3V。保留 SM712、A/B 串联保护。R100/R101 各 270Ω/1% 形成 A 上拉、B 下拉，补足终端负载下的空闲偏置；R32 120Ω 终端默认不装，仅按总线端点需要装配。原 THVD2410 的故障耐压能力不能继承到 MAX3485。[ADI 数据手册](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX3483-MAX3491.pdf)
- U7 BL13232ETS（BL13232E 系列，TSSOP16，C2999161）：3.3V RS232。11脚 DIN1 接 FIELD_TX，12脚 ROUT1 接 232_RX_RAW，13脚 RIN1 和14脚 DOUT1 接现场收发；闲置通道 8脚 RIN2 和10脚 DIN2 接地，7脚 DOUT2 和9脚 ROUT2 不连接。C30/C31 飞跨电容、C32/C33 储能电容各100nF，C34 电源去耦100nF。[贝岭数据手册](https://www.belling.com.cn/media/file_object/bel_product/BL13232E/datasheet/BL13232E_V1.3_en.pdf)
- U8 SN74LVC1T45DCKR（C9382）：保留 TTL TX 的 3.3V→约5.05V 转换，两侧去耦保留。端口不输出5V电源。[TI 数据手册](https://www.ti.com/lit/ds/symlink/sn74lvc1t45.pdf)
- U12 SN74LVC1G11DCKR（C529281）：3.3V 供电的三输入与门，输入允许5.5V，兼做5V TTL 接收转换及三路合并。1脚接485_RX_RAW，3脚接232_RX_RAW，6脚接TTL_RX_BUF，4脚输出FIELD_RX，2脚地、5脚3.3V，C38去耦。R37 100k 定义 TTL 空闲高；R38 10k 上拉 485_RX_RAW，保证 /RE 禁用期间不悬空。[TI 数据手册](https://www.ti.com/lit/ds/symlink/sn74lvc1g11.pdf)

原板二极管合并属于测量支持的候选拓扑，器件型号/极性未完全确认。本版使用与门替代，避免二极管压降叠加收发器最坏 VOL 后对 ESP32-C5 低电平门限余量过小。不照抄原板 DI 接地的逐位发送方案，保留按帧 DE 控制。

''' + s[b:]
s=s.replace('BOM-V0.6.csv','BOM-V0.11.csv').replace('默认装配 167 件，包含 65 个电阻；PCB 上保留 173 个器件位置、66 个电阻位置。','默认装配 148 件；PCB 上保留 154 个器件位置、56 个电阻位置。')
f.write_text(s,encoding='utf-8')
f=p/'reports/RK_WB4G_V2串口接口候选原理图-2026-10-12.md';s=f.read_text(encoding='utf-8');s=s.replace('尚未修改现有原理图、PCB或已确认规格；本文件不是生产网表。','此为原板测量与候选分析的历史记录，不是生产网表。现有工程已按 V0.11 修改：MAX3485、BL13232E、三输入与门合并接收，保留按帧 DE 控制；详见 [V0.11 修改与验证记录](V0.11接口修改与验证记录.md)。下面的二极管及逐位方向方案保留用于追溯，不代表最终实施。');f.write_text(s,encoding='utf-8')
f=p/'scripts/README.md';s=f.read_text(encoding='utf-8');s+='\nV0.11 当前工程 UUID 为 1d7fb27b7ad9306bc25c90ee476429c9e681ffecce79136ba05149eca7bba1b0。revision-v11.json 和实际导出的 V0.11 网表为本版依据。prepare/revise/prune/sync/apply 脚本为阶段性操作记录，不具备幂等性，不可对完成后的工程重放；恢复应使用已导出的 epro2。verify-interface-v11.py 只读核对原理图和 PCB 快照，并生成验证记录及 BOM。\n';f.write_text(s,encoding='utf-8')
