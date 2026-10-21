from pathlib import Path
import json,shutil,zipfile,hashlib
R=Path('PCB');E=R/'eda';M=R/'manifests';D=R/'docs'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
v=load(M/'leadholefix-manufacturing-verification-v13.json');backup=load(M/'lead-hole-backup-v13.json')['directory']
for tail in ['BOM-99.csv','CPL-99-Top.csv']:
 a=E/f'DTU-V0.13-Silkholefix-{tail}';b=E/f'DTU-V0.13-Leadholefix-{tail}';shutil.copy2(a,b);assert a.read_bytes()==b.read_bytes()
doc=D/'V0.13-焊脚距孔修正记录.md'
doc.write_text(f'''# V0.13 焊脚距孔修正记录

2026-10-16。用户截图为“元件焊脚到孔的距离”，4条危险分别Q1两条0 mm、J4两条0.02 mm，目标良好间距≥0.25 mm。此项与此前端子同位号自碰撞不同，不能混用解释。

定位使用原生可编辑工程、焊盘、钻孔和封装PIN_SOLDERING（50层）/PIN_FLOATING（51层）几何。Q1接地孔026b68367e7fffbc的孔口与其焊脚区域相交，间距0；J4/SIM_VDD孔bd31757caf9c21db到对应供电脚轮廓约0.024989 mm，按两位小数与截图0.02吻合。截图没有展示4项逐一定位图，因此“每处重复报告两次”属于与数值相符的推断，未宣称厂家内部对象已完全解析。

修改前备份：{backup}。

| 位置 | 旧孔中心/mm | 新孔中心/mm | 孔边至相关库焊脚轮廓/mm |
|---|---|---|---:|
| Q1/GND | 27.350,40.925 | 26.700,40.925 | 0.425710 |
| J4/SIM_VDD | 20.775,26.275 | 20.525,26.675 | 0.325035 |

两孔均保持外径0.45 mm、钻孔0.20 mm和双面盖油参数，不以缩小焊盘或孔环消除告警。Q1地线改为就近引出。SIM供电孔同时整理顶层/底层/内层原有连接；为让开该孔，重新走了一段顶层SIM_CLK。删除两段与同网连接重复的供电线，其余5条既有线更新路径。过孔数306不变，总钻孔322不变，走线图元509→507；未增加器件、未改位置、焊盘或板框。

原生铺铜已全部重建、保存、重新打开。原生PCB DRC为0项。源文件逐项比对，仅2个VIA位置、7个POLY（5改2删）、3个POURED重建结果有变化；元件、焊盘绑定、丝印、规则和其余对象不变。实际原生铜线数据与计划逐坐标核对相符。独立非铺铜几何核对未引入新冲突；工具使用0.1528 mm阈值时仍显示2个未改动TTL_RX_EXT/VDD_3V3旧组合约0.151961 mm，两个组合与本轮前完全一致，不能把该辅助结果写成全局0冲突；原生规则DRC为0。

实际生产Gerber检查：两处相关库焊脚至孔边间距如上；孔边至全部顶层阻焊开窗分别约0.324/0.347 mm，外圈铜至开窗分别约0.199/0.222 mm；全部322孔最小孔壁间距{v['minimumDrillWallGapMm']:.6f} mm。之前丝印避孔修正保持：丝印距孔最小{v['silkToDrillWallMinimumGapMm']:.6f} mm、距阻焊开窗{v['silkToMaskMinimumGapMm']:.6f} mm。导出孔位已核对新孔存在、旧孔消失。四层铜和PTH钻孔采用新原生导出；7个不涉及的生产文件经几何核对后与Silkholefix前版按字节一致，包括丝印、阻焊、钢网、板框及NPTH钻孔。继续去除原生导出中已确认的4角NPTH微小占位铜点和数值级盖油残点。

板规格60×70 mm、4层、单面贴装，104封装/99件默认实装，BOM/CPL因所有元件位置和方向不变而逐字节沿用配套复制。端子封装和针序不变。

限制：本地使用库焊脚几何核对，不等于厂家DFM引擎；4行与2个数值位置的对应仍须新文件重跑确认。另发现J4的既有GND焊脚模型到另一盖油过孔约0.125 mm，未与此次截图0.02项匹配，保留为待定位/工艺确认项，不以它解释此次两条0.02提示。此前端子模型同位号告警、五组装配余量告警及其他工艺事项仍待确认，整板厂家DFM尚未通过。

生产文件：DTU-V0.13-60x70-Leadholefix-Gerber.zip；工程：DTU-V0.13-60x70-Leadholefix.epro2。复查时使用本版配套文件，不要混用前版钻孔。
''',encoding='utf8')
readme=E/'DTU-V0.13-Leadholefix-README.md';readme.write_text('''# V0.13 焊脚避孔复查版

当前Leadholefix版已将Q1接地孔和J4/SIM供电孔移出相关焊脚区域；两处孔边到库焊脚轮廓分别约0.426/0.325 mm。原生PCB DRC=0，仍需厂家重新检查“元件焊脚到孔的距离”。

60×70 mm、4层、单面贴装。104封装/99件默认实装、306过孔、322钻孔。器件和焊盘位置、方向、针序不变。BOM/CPL逐字节沿用配套复制。

局部SIM供电与时钟线已调整并重建铺铜，生产Gerber的四层铜/PTH孔均更新，勿混用旧版。之前丝印距孔0.262 mm、距阻焊0.289 mm保持。工程、Gerber、BOM/CPL及修正记录在复查包内。

全部厂家DFM尚未通过。端子同位号模型提示、装配余量预警、另一个J4地脚模型到盖油孔约0.125 mm及原有工艺待确认项见配套记录。
''',encoding='utf8')
items=[E/'DTU-V0.13-60x70-Leadholefix.epro2',E/'DTU-V0.13-60x70-Leadholefix-Gerber.zip',E/'DTU-V0.13-Leadholefix-BOM-99.csv',E/'DTU-V0.13-Leadholefix-CPL-99-Top.csv',readme,doc,D/'V0.13-精简丝印版接口说明.md',D/'V0.13-七项装配余量预警复核记录.md',D/'V0.13-元件距元件九项复核记录.md',M/'leadholefix-manufacturing-verification-v13.json',E/'DTU-V0.13-Leadholefix-Q1-detail.png',E/'DTU-V0.13-Leadholefix-J4-detail.png']
package=E/'DTU-V0.13-60x70-焊脚避孔修正复查包.zip'
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
 for p in items:z.write(p,p.name)
for p in [items[0],items[1],package]:
 with zipfile.ZipFile(p) as z:assert z.testzip() is None
current=load(M/'current-pcb-delivery-v13.json');current.update({'revision':'V0.13 焊脚避孔修正 2026-10-16','status':'Q1接地孔与SIM供电孔避让完成，待新资料重跑厂家DFM','nativeProject':str(items[0].resolve()),'productionGerber':str(items[1].resolve()),'deliveryArchive':str(package.resolve()),'actualCopperManifest':'lead-hole-actual-routing-v13.json','actualSourceSnapshot':'lead-hole-reopened-source-v13.json','backupDirectory':backup,'leadHoleReview':str(doc.resolve()),'manufacturingVerification':'leadholefix-manufacturing-verification-v13.json','factoryDfmPassed':False,'files':[{'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in items]})
current['openDfmItems']=[x for x in current['openDfmItems'] if not x.startswith('焊脚距孔：')]+['焊脚距孔：Q1接地孔与J4/SIM供电孔已移位，相关库焊脚到孔边约0.426/0.325mm；4条提示须新Gerber复查。另有J4地脚库轮廓至既有盖油孔约0.125mm，未匹配此次0.02项，待定位/工艺确认。'];save(M/'current-pcb-delivery-v13.json',current)
for a,b in [('lead-hole-drc-v13.json','check-pcb-v13.json'),('lead-hole-actual-routing-v13.json','final-connected-routing-v13.json')]:shutil.copy2(M/a,M/b)
for a,b in [(items[0].name,'DTU-V0.13-60x70-DFM-review.epro2'),(items[1].name,'DTU-V0.13-60x70-SMT-4L-Gerber-DFM.zip'),(package.name,'DTU-V0.13-60x70-验收资料包.zip'),(readme.name,'DTU-V0.13-README.md')]:shutil.copy2(E/a,E/b)
print(json.dumps({'project':str(items[0]),'gerber':str(items[1]),'package':str(package),'backup':backup},ensure_ascii=True))
