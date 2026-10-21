import csv, json, re
from collections import defaultdict
from pathlib import Path
import openpyxl

root = Path('D:/DTU')
order_path = Path('D:/download/订单数据 (1).xlsx')
bom_path = root/'PCB/eda/DTU-V0.14.4-Threefix-BOM-99.csv'
models = json.loads((root/'outputs/bom-20261019/manufacturer-models.json').read_text(encoding='utf-8-sig'))
with bom_path.open(encoding='utf-8-sig', newline='') as f:
    bom = list(csv.DictReader(f))
groups = defaultdict(list)
for p in bom:
    groups[p['LCSC Part #']].append(p)
sheet = openpyxl.load_workbook(order_path,read_only=True,data_only=True)['订单数据']
orders = {n:list(row) for n,row in enumerate(sheet.values,1) if n>1 and row[0]}
# Explicit correspondence to original BOM; quantities below are pieces per sale unit.
mapping = [
 (2,'C128504',5,'同型号','6SVPC220MV'),
 (3,'C83465',5,'同型号','SWPA8040S6R8MT'),
 (4,'C434808',10,'尺寸待核','国产20279-001E-01'),
 (5,'C7429562',10,'尺寸待核','PH2.0立贴4P'),
 (6,'C439873',1,'同型号','1812L200/16DR'),
 (7,'C72041',10,'可替换：蓝色0603，6T版本','19-217/BHC-ZL1M2RY/6T'),
 (8,'C72043',10,'可替换：绿色0603，6T版本','19-217/GHC-YR1S2/6T'),
 (9,'C85401',1,'同型号','PESD5V0U1UL,315'),
 (10,'C2827694',1,'同型号','PESD5V0S1BA'),
 (11,'C529281',1,'同型号','SN74LVC1G11DCKR'),
 (12,'C544759',1,'同型号','TLV75901PDRVR'),
 (13,'C712347',1,'品牌变更：基本规格匹配，需核实来料尺寸/标识','晶导微SMF7.0CA'),
 (14,'C5186957',1,'同型号','TXU0202DCUR'),
 (15,'C2999161',1,'同型号','BL13232ETS'),
 (16,'C1545222',1,'引脚封装匹配，首板验证3.3V与通信','SP3485EN-L/TR'),
 (17,'C840642',50,'阻值正确，排阻尺寸/内部连接待核','通用0603×4，22Ω±1%'),
 (18,'C149100',50,'阻值正确，排阻尺寸/内部连接待核','通用0603×4，100kΩ±1%'),
 (19,'C784821',50,'阻值正确，排阻尺寸/内部连接待核','通用0603×4，10kΩ±1%'),
 (20,'C784824',50,'阻值正确，排阻尺寸/内部连接待核','通用0603×4，1kΩ±1%'),
 (21,'C22966',100,'可替换：同阻值/0603/1%/0.1W','RC0603FR-07270RL'),
 (22,'C4184',100,'可替换：同阻值/0603/1%/0.1W','RC0603FR-0720KL'),
 (23,'C23242',100,'可替换：同阻值/0603/1%/0.1W','AC0603FR-0775KL'),
 (24,'C21190',100,'可替换：同阻值/0603/1%/0.1W','RC0603FR-071KL'),
 (25,'C21189',100,'同型号','0603WAF0000T5E'),
 (26,'C22775',1,'可替换：100Ω，精度提升至0.5%','RC0603DR-07100RL'),
 (27,'C25803',100,'同型号','0603WAF1003T5E'),
 (28,'C23138',100,'可替换：同阻值/0603/1%/0.1W','AC0603FR-07330RL'),
 (29,'C22859',100,'可替换：同阻值/0603/1%/0.1W','RC0603FR-0710RL'),
 (30,'C23345',100,'可替换：22Ω/0603/1%/0.1W','RS-03K22R0FT'),
 (31,'C25804',100,'同型号','0603WAF1002T5E'),
 (32,'C14858',1,'同型号','CL10C101JB8NNNC'),
 (33,'C441864',1,'同型号','GRM21BR61A226ME44L'),
 (34,'C1663',1,'同型号','CL10C330JB8NNNC'),
 (35,'C14860',1,'同型号','CL31B106KAHNNNE'),
 (36,'C15849',1,'同型号；原BOM简写16V与完整型号描述需统一','CL10A105KB8NNNC'),
 (37,'C14663',1,'同型号','CC0603KRX7R9BB104'),
 (38,'C308787',1,'同型号','UMH9NTN'),
 (39,'C72044',1,'颜色变更：红→橙；接受颜色变化才替换','19-217/S2C-AL1M2VY/3T'),
 (40,'C45961',1,'同型号','PESD5V0F1BL,315'),
 (41,'C399256',1,'品牌变更：CJ准确数据表待核','CJ SMF12CA'),
 (42,'C127543',1,'品牌变更：RS485专用SM712，核实引脚/来料','UMW SM712'),
 (43,'C8678',1,'可替换：SMA，3A/40V','UMW SS34'),
 (44,'C1981435',1,'可替换：SMB，12V单向600W','UMW SMBJ12A'),
 (45,'C48982537',1,'同型号，实际装配U2','ML307R-DL'),
 (47,'C2158012',1,'候选替料：需要首板电源验证','SCT2330TVBR'),
 (48,'C266888',1,'同型号','SMN-303'),
 (49,'C49308183',1,'可替换：1U同尺寸；软件按8MB PSRAM配置','ESP32-C5-WROOM-1U-N8R8'),
 (50,'C97502',1,'同型号，DRT/SOT9X3，不是普通SOT23','TPD2EUSB30DRTR'),
]
assert len(mapping)==len(groups)==48
assert {code for _,code,_,_,_ in mapping}==set(groups)
assert len({row for row,*_ in mapping})==48
assert set(orders)-{row for row,*_ in mapping}=={46,51}
assert len(bom)==99
details=[]
for row,code,pack,status,new in mapping:
    qty=int(orders[row][2]); need=len(groups[code])*5
    details.append(dict(row=row,code=code,refs=','.join(p['Designator'] for p in groups[code]),
      original=models[code]['model'],new=new,per_board=len(groups[code]),need=need,
      sale_units=qty,pack=pack,pieces=qty*pack,spare=qty*pack-need,status=status))
assert all(d['spare']>=0 for d in details)
out=root/'outputs/bom-review-20261020/更新订单采购核对-20261020.md'
lines=['# 更新订单与 V0.14.4 BOM 核对','',
 '核对日期：2026-10-20；生产数量：5块；原BOM保持不变。', '',
 '来源：订单数据 (1).xlsx 的“订单数据”A:E，以及当前发布的 Threefix-BOM-99.csv。完整型号由原型号汇总映射补全。', '',
 '## 结论','',
 '- 原BOM共48个料号组、每板99件，5板需495件。采购中48项电子器件均能找到对应位置，另有镊子、加热台两项工具。',
 '- 按已选款式/商品标题明确的包装数换算，48项数量全部达到5板最低用量；这是订单数量核对，不代表所有替料已通过兼容验证。',
 '- ESP32款式已明确为1U-N8R8；ML307R款式明确为DL；PH2.0款式明确为立贴4P；四种排阻阻值正确。',
 '- 未买原红色LED，买的是橙色19-217/S2C-AL1M2VY/3T。若保留红色要求，需要换成原红灯或另核实的红色替料。',
 '- PH2.0插座、国产射频座、通用排阻缺尺寸/内部连接证明；电源芯片SCT2330需首板验证；CJ SMF12CA缺准确品牌数据表。', '',
 '## 不改PCB的替料边界','',
 '| 位置 | 采购变更 | 结论及剩余核对 |',
 '|---|---|---|',
 '| U1 | N8R4→ESP32-C5-WROOM-1U-N8R8 | 已选1U外接天线款，18×21.2mm，原PCB封装适配；软件按实际PSRAM配置。当前GPIO15对应焊盘未接出，不与PSRAM冲突。 |',
 '| U2 | ML307R-DL | 与原型号一致，5个正好够。此前仅在DFM暂时排除，不是实际不贴。 |',
 '| U4 | AP63300WU-7→SCT2330TVBR | TSOT23-6引脚与0.8V反馈参考匹配，但开关频率从500kHz变400kHz。现有6.8µH及输出电容下需测启动、输出纹波、LTE发射负载突变和温升；目前不能当作已验证直接替代。 |',
 '| U6 | MAX3485ESA+→SP3485EN-L/TR | SO8尺寸与引脚匹配，可在原PCB使用；按3.3V±5%核对供电并做首板RS485收发验证。 |',
 '| J1/J2/J3 | ZX-HY2.0-4PLT→通用PH2.0立贴4P | 方向/针数已确认；2mm间距仍不足以确认相容，要比对信号脚位置、焊接脚伸出量、外壳固定焊脚及外形尺寸。无图纸前不批准免改板替换。 |',
 '| J5 | U.FL-R-SMT(10)→国产20279-001E-01一代 | 订单明确为国产兼容件，不能等同原装I-PEX；若依20279-001E-01标准三焊脚尺寸制作则可适配，但仍需卖家尺寸图或实物对位。 |',
 '| RN1/RN2/RN3/RN4/RN5 | CAY16→通用0603×4 | 1k/10k/100k/22Ω选择正确，1%可代原5%；还须确认4个独立电阻、8脚、3.2×1.6mm、0.8mm脚距及端子形状，不能用共端型。 |',
 '| D30/D33 | R6C红→S2C橙 | 0603、电压档相近，原PCB可装；显示颜色变化需要用户确认。 |',
 '| D31/D34/D36、D32/D35/D37 | 绿/蓝3T→6T | 对应色别和0603尺寸匹配；绿色同为20mA测试档，蓝色同为5mA测试档，电压档适合现有指示灯电路，可替换；不是所有3T/6T后缀都可一概互换。 |',
 '| D1/D4 | MDD SS34→UMW SS34；Vishay SMBJ12A/54→UMW SMBJ12A | 所选SMA 3A/40V与SMB 12V单向600W规格匹配，可替换。D4保持A单向款。 |',
 '| D5 | SM712→UMW SM712 | 应为RS485用+12V/-7V非对称保护阵列、SOT23，核对1/2接A/B、3接GND；应依具体厂商数据表和来料引脚图装配。 |',
 '| D6 | MCC SMF7.0CA-TP→晶导微SMF7.0CA | 标称7V双向200W、SOD123FL匹配；需核实来料外形和精确电气规格，不能只认7V字样。 |',
 '| D7 | SUNMATE SMF12CA→CJ SMF12CA | 标称型号/封装匹配，未取得此次CJ来料的准确数据表，暂不标完全等效；核对12V双向200W及钳位、电流、尺寸。 |',
 '| 8组普通电阻 | 原厚声→国巨/其他对应料号 | 阻值、0603、0.1W匹配，1%/0.5%均达到原要求，可替换。详见逐项表。 |', '',
 'TXU0202DCUR、TPD2EUSB30DRTR、TLV75901PDRVR、SN74LVC1G11DCKR、BL13232ETS、UMH9NTN、SMN-303、L1、F1及7组电容均保留原完整型号。TPD封装保持DRT/SOT9X3，不能按普通SOT23焊盘理解。', '',
 '## 全部48项：按器件只数换算','',
 '包装数量来自“型号款式”，若款式为暂无则采用标题明确的5只/10只/100只；无包装说明的器件按1只/商品数量计算。排阻按一个四联器件算1只，未拆成4个电阻。仅按订单表记录计算，不推断实物已收货。', '',
 '| 订单行 | 位号 | 原完整型号 | 采购型号/规格 | 每板 | 5板需 | 包装×份数 | 采购只数 | 余量 | 核对结果 |',
 '|---:|---|---|---|---:|---:|---:|---:|---:|---|']
for d in details:
    lines.append('| {row} | {refs} | {original} | {new} | {per_board} | {need} | {pack}×{sale_units} | {pieces} | {spare} | {status} |'.format(**d))
lines += ['', '## 正好够5板、没有备件的项目','',
 '| 项目 | 位号 | 采购/需要 |','|---|---|---:|']
for d in details:
    if d['spare']==0: lines.append(f"| {d['new']} | {d['refs']} | {d['pieces']}/{d['need']} |")
lines += ['',
 '以上项目若手工装配丢件或损坏，可能需要补货；这是备料余量提示，不是数量漏买。', '',
 '## 订单外的配套与限制','',
 '- 当前默认不贴的C50、C51、R32、J6、J7不计入本次遗漏；不应因旧版器件库出现而补买。',
 '- 订单中未见外接天线、SIM卡、PH2.0配套线束和电源配套；如手边没有，整机调试需另外准备。LTE天线与ESP32-C5双频天线需分别选合适规格，不能因为接头相似就当作同一天线。',
 '- 镊子和HP20加热台是工具，不计入PCB BOM。',
 '- 本次只核对器件，不代表原PCB的所有DFM检查已经通过。原制造文件和BOM均未修改；替料待用户确认后再更新。', '',
 '## 主要技术依据','',
 '- [Espressif 模组型号、尺寸和引脚](https://documentation.espressif.com/esp32-c5-wroom-1_wroom-1u_datasheet_en.html)',
 '- [SCT2330 数据表](https://www.silicontent.com/uploads/20250318/0125e1f51ea843e8e7208246dbaabc7f.pdf)',
 '- [AP63300 数据表](https://www.diodes.com/datasheet/download/AP63300_AP63301.pdf)',
 '- [SP3485 数据表](https://www.maxlinear.com/ds/sp3485.pdf)',
 '- [Bourns CAY16 原排阻数据表](https://www.bourns.com/data/global/pdfs/CATCAY.pdf)',
 '- [Everlight 元件目录：橙色S2C与原绿色3T](https://www.everlight.com/wp-content/uploads/2021/02/2019_Component_Catalogue.pdf)',
 '- [Everlight 绿色6T数据表](https://www.everlighteurope.com/custom/files/datasheets/DSE-0025583.pdf)',
 '- [I-PEX 20279 原厂尺寸参考；不能替代此次国产件图纸](https://www.i-pex.com/sites/default/files/downloads/pdf/2D_MHF_I_RECEPTACLE_20279C29.pdf)',
 '- [UMW SMBJ 系列数据表](https://www.umw-ic.com/static/pdf/62a30f50b229ed3e3eee960a7e35a088.pdf)',
 '- [UMW SM712 数据表](https://www.umw-ic.com/static/pdf/2d03ecb92429eef2021ebedda8cc2e9f.pdf)',
 '']
out.write_text('\n'.join(lines),encoding='utf-8')
(root/'outputs/bom-review-20261020/order-bom-mapping.json').write_text(json.dumps(details,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'report':str(out),'groups':len(details),'parts_per_board':len(bom),'required_5boards':sum(d['need'] for d in details),'shortages':[d for d in details if d['spare']<0], 'zero_spares':[{k:d[k] for k in ['refs','new','pieces','need']} for d in details if d['spare']==0]},ensure_ascii=False,indent=2))
