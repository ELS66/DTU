"""Publish the dedicated ML307R footprint revision and matched assembly data."""
from pathlib import Path
import json,zipfile,csv,shutil,hashlib,math
R=Path('PCB');M=R/'manifests';E=R/'eda';D=R/'docs'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
v=load(M/'ml307fix-manufacturing-verification-v13.json');pid=load(M/'ml307fix-project-id-v13.json');backup=load(M/'ml307fix-backup-v13.json')['directory'];shifts=load(M/'ml307fix-component-shifts-v13.json');oldcs=load(M/'silkclean-pcb-pads-v13.json')['result'];newcs=load(M/'ml307fix-final-pads-v13.json')['result'];oldby={c['ref']:c for c in oldcs};newby={c['ref']:c for c in newcs}
assert v['PCB_DRC']==0 and v['exportedCapsulePadCountVerified']==48 and len(newcs)==104
# Store process review items separately from the completed footprint/data checks.
v['manufacturer3mmModuleNeighborClearanceFullyMet']=False
v['moduleNeighborClearanceExamplesMm']={'R64':1.125,'Q1':1.443,'C80':1.725,'C85':1.725,'R50_R60_R61':2.075}
v['engineeringLimitations']+=['The manual recommends at least3mm between module and nearby parts; the compact layout has some1.125-2.442mm body gaps. Factory solder/rework process review remains required.']
save(M/'ml307fix-manufacturing-verification-v13.json',v)
move_table='\n'.join(f"| {ref} | {oldby[ref]['x']*.0254:.3f}, {oldby[ref]['y']*.0254:.3f} | {newby[ref]['x']*.0254:.3f}, {newby[ref]['y']*.0254:.3f} | {'默认不装' if ref in ['C50','C51'] else '实装'} |" for ref in ['J5','R50','R60','R61','C50','C51'])
doc=D/'V0.13-ML307R专用封装修正记录.md'
doc.write_text(f'''# V0.13 ML307R 专用封装修正记录

2026-10-16。ML307fix为当前复查版，基于Leadholefix继续修改。备份：{backup}。新版已在嘉立创EDA独立工程副本中打开，原项目及历次唯一文件保留。

## 结果

U2不再沿用MC661名义封装与不相符的焊脚尺寸。依据中移物联网《ML307R硬件设计手册 AT版本适用 V1.0.1》第55～56页的机械底视图与PCB推荐封装，重建专用封装DTU_ML307R_DL_LCC48_LGA61_OFFICIAL_V1_0_1。此为按手册重建的工程封装，不是厂家发布的原始CAD库，也不代表厂家认证。

48个外围铜焊盘改为2.60×0.60 mm、圆端R0.30 mm，中心向外调整约0.40 mm；61个内圈LGA焊盘保持1.00×0.70 mm或中央1.30×1.30 mm，对中心坐标作标称网格归整（原亚微米数值偏差）。109个焊脚模型按手册名义尺寸重建：外围金属区域宽0.60 mm，中央六块方形区域1.30 mm；未删除焊脚模型或为了隐藏告警削小真实金属区域。封装焊盘唯一ID、脚号、原理图及逐针网络绑定全部保留。

原生参数中矩形圆角字段采用比例；最终设为短边半宽的100%，通过实际Gerber核对为R0.30 mm。已逐个核对48个导出铜/钢网圆端及阻焊开窗，确认不是仅改名称或保留近似矩形。

规格保持60×70 mm、四层、正面贴装，104个封装/99件默认实装。两个模组方向、位置及上沿对齐不变；底部三个HY2.0座、净空、四个安装孔、两组5孔下载口和8个指示灯位置保留。

## 周边布局与布线

| 器件 | 原坐标/mm | 新坐标/mm | 装配 |
|---|---|---|---|
{move_table}

J5天线座上移1.5 mm，更靠上边缘；R50及射频预留电容、USB电阻让开新长焊盘。6个器件方向均未变；其中C50/C51仍默认不装，配套CPL只改变4个实装位置。

对受影响的47条旧走线局部替换，新增48个走线图元，总数507→508。射频LTE_ANT/LTE_RF_FEED均留在顶层，保留原0.35 mm线宽，缩短原绕行，不增加射频信号过孔。USB两支网络的几何长度总和差约{v['USB_DP_DM_GeometrySumSkewMm']:.3f} mm；该数值不是TDR测量，也不代替差分耦合/阻抗验证。电源一段从0.8 mm改为0.6 mm，其他供电连接及电容不变，动态压降和温升仍待首板验证。

14个原有过孔移位，避免被扩大的焊盘覆盖；两处新增过孔用于LED_LTE_G_N信号换层，避让模组焊盘。308个过孔、324个总钻孔（原306/322），不增加器件。新增孔仍为外径0.45/钻孔0.20 mm，双面盖油，未为避让缩小孔环。

## 验证

- 全部铺铜原生重建、保存、关闭再打开，PCB DRC=0。
- 原生实际铜线与计划逐坐标比对一致；整套工程比较仅涉及预期PCB对象及U2封装。原理图、符号、电气网络、脚号与其他封装无改动。导入器删除1项默认打开图页配置元数据，未改变原理图内容。
- PCB变化为95个POLY记录（47删48增）、16个VIA记录（14移2增）、6个COMPONENT位置、6个隐藏属性位置、3个POURED重建结果。U2库修改109个PAD、109个焊脚FILL及名称/说明记录。
- 独立非铺铜辅助扫描未新增冲突；仍有2个未改动TTL_RX_EXT/VDD_3V3组合约0.151961 mm，略小于辅助阈值0.1528 mm，原生规则DRC为0，不能将辅助扫描描述为全局0项。
- 库48层全部默认实装本体无重叠、无整体放大5%后的相交；该二维检查不等于厂家3D检查。
- 实际Gerber最小孔壁间距{v['minimumDrillWallGapMm']:.6f} mm；14个移位孔外圈铜距全部顶层开窗最小{v['minimumMovedViaAnnulusMaskGapMm']:.6f} mm，两新增孔分别约0.260/0.185 mm。此前Q1/J4避孔位置保持。
- 丝印距孔最小{v['silkToDrillWallMinimumGapMm']:.6f} mm，距阻焊开窗{v['silkToMaskMinimumGapMm']:.6f} mm。顶/底丝印、底层阻焊、板框及NPTH钻孔与前版逐文件字节一致。
- 四层铜、顶层阻焊、钢网及PTH钻孔采用本版新导出；仍清理4角NPTH的16个数值级铜占位点与盖油微小数值残点。只交付12个生产文件，不混用旧钻孔或旧钢网。
- 新BOM/CPL均为99件，位号集合一致；逐项核对原生BOM的供应商料号与封装，CPL采用原生新导出Mid坐标。U2封装名称更新；4个实装位置已同步，不得继续用旧版CPL。

## 尚待厂家/首板确认

厂家DFM尚未运行通过。本地修复不等于用户截图全部85项均消除。LCC脚跟/半孔金属与厂家推荐圆端焊盘存在形状差异，通用PIN内边界算法仍可能给出提示，应结合本版真实模型及所附手册定位；不能重新套回MC661模型，也不应通过删模型/改阈值消红。

手册另建议模组周边至少3 mm空间以利焊接和维修，现有紧凑布局部分本体间隙约1.125～2.442 mm（例如R64/Q1/电容及USB电阻），未完全达到该建议。此轮仅完成封装与受影响布线修正，需贴装厂评估实际回流和返修工艺；若要求全周3 mm净空，需进一步扩大/重排局部空间，不能将本轮当作该项通过。射频50Ω、USB90Ω须按最终叠层核定，当前线宽不构成阻抗认证。此前端子同位号模型提示、五组装配余量提示、J4另一接地脚附近盖油孔约0.125 mm及其他待确认项继续保留；电源瞬态、热和首板功能尚待测试。

## 文件

- 工程：DTU-V0.13-60x70-ML307fix.epro2；工程副本目录PCB/native-ML307fix-final（内部友好名称仍保留历史50x60文字，真实板框已核对60×70 mm）。
- Gerber：DTU-V0.13-60x70-ML307fix-Gerber.zip。
- 装配：DTU-V0.13-ML307fix-BOM-99.csv及DTU-V0.13-ML307fix-CPL-99-Top.csv。
- 验证：ml307fix-manufacturing-verification-v13.json及ml307fix-exported-pad-check-v13.json。
- 原始手册：https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1189/M307R_Hardware_Datasheet.pdf （厂家文档，由M5Stack托管）。包内附同一PDF及第55/56页尺寸图。
''',encoding='utf8')
readme=E/'DTU-V0.13-ML307fix-README.md';readme.write_text('''# V0.13 ML307R 专用封装修正复查版

当前ML307fix版已按手册重建ML307R-DL专用封装及109个焊脚模型，48个外围焊盘2.60×0.60 mm、R0.30圆端。天线座、射频匹配预留及USB电阻同步调整，尺寸仍60×70 mm，4层，正面贴装，104封装/99件默认实装。原生PCB DRC=0，厂家DFM未放行。

请用本包新的Gerber+BOM+CPL一起复查。U2封装名已更新，J5/R50/R60/R61贴装坐标已改变；不能混用旧CPL、旧钢网或钻孔。两预留电容C50/C51仍不装。过孔308、总钻孔324（新增两孔用于指示灯线换层）。

工程副本位于PCB/native-ML307fix-final，PCB已在EDA打开。工程内部标题仍有历史50x60文字，以已核对60×70 mm板框及本包文件名为准。

本轮是按原厂手册重建的工程封装，不是厂家原始CAD认证。通用PIN内边界提示仍需结合LCC圆端/半孔几何复查，模组周边3 mm建议净空部分未满足，需工艺评审；最终射频/USB阻抗、温升及首板功能尚待验证。其余原有DFM待确认项见修正记录。不要把原生DRC=0当作整板厂家DFM通过。
''',encoding='utf8')
items=[E/'DTU-V0.13-60x70-ML307fix.epro2',E/'DTU-V0.13-60x70-ML307fix-Gerber.zip',E/'DTU-V0.13-ML307fix-BOM-99.csv',E/'DTU-V0.13-ML307fix-CPL-99-Top.csv',readme,doc,D/'V0.13-精简丝印版接口说明.md',M/'ml307fix-manufacturing-verification-v13.json',M/'ml307fix-exported-pad-check-v13.json',E/'DTU-V0.13-ML307fix-Gerber-preview.png',E/'DTU-V0.13-ML307fix-RF-USB-detail.png',R/'references/ML307R-Hardware-AT-V1.0.1.pdf',R/'references/ML307R-hardware-page-55.png',R/'references/ML307R-hardware-page-56.png']
package=E/'DTU-V0.13-60x70-ML307R专用封装修正复查包.zip'
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
 for p in items:z.write(p,p.name)
for p in [items[0],items[1],package]:
 with zipfile.ZipFile(p) as z:assert z.testzip() is None
current=load(M/'current-pcb-delivery-v13.json');current.update({'revision':'V0.13 ML307R专用封装修正 2026-10-16','status':'专用封装及RF/USB适配完成，原生DRC0；待厂家DFM/工艺评审','projectUuid':pid['uuid'],'nativeWorkspaceDirectory':pid['nativeWorkspaceDirectory'],'vias':308,'drilledHoles':324,'pcbDrcIssues':0,'nativeProject':str(items[0].resolve()),'productionGerber':str(items[1].resolve()),'deliveryArchive':str(package.resolve()),'actualCopperManifest':'ml307fix-actual-routing-v13.json','actualPadManifest':'ml307fix-final-pads-v13.json','actualSourceSnapshot':'ml307fix-reopened-source-v13.json','backupDirectory':backup,'u2FootprintBoundaryReview':str(doc.resolve()),'manufacturingVerification':'ml307fix-manufacturing-verification-v13.json','factoryDfmPassed':False,'files':[{'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in items]})
current['openDfmItems']=[s for s in current['openDfmItems'] if not s.startswith('U2引脚边界：')]+['U2引脚边界：专用109脚模型及48个推荐圆端焊盘已按手册修复并导出核对，需使用新Gerber+BOM+CPL重跑厂家DFM；通用半孔/圆端边界提示不能预先判定消除。','模组周边净空：手册建议至少3mm，当前紧凑布局部分1.125～2.442mm，待贴装/返修工艺评审。','RF/USB：布局已适配，0.35mm射频线宽保留、USB几何长度和差约0.246mm，最终阻抗须按生产叠层核定。']
save(M/'current-pcb-delivery-v13.json',current)
for a,b in [('ml307fix-pcb-drc-v13.json','check-pcb-v13.json'),('ml307fix-actual-routing-v13.json','final-connected-routing-v13.json')]:shutil.copy2(M/a,M/b)
for a,b in [(items[0].name,'DTU-V0.13-60x70-DFM-review.epro2'),(items[1].name,'DTU-V0.13-60x70-SMT-4L-Gerber-DFM.zip'),(package.name,'DTU-V0.13-60x70-验收资料包.zip'),(readme.name,'DTU-V0.13-README.md'),('DTU-V0.13-ML307fix-BOM-99.csv','DTU-V0.13-BOM-99.csv'),('DTU-V0.13-ML307fix-CPL-99-Top.csv','DTU-V0.13-CPL-99-Top.csv')]:shutil.copy2(E/a,E/b)
# Current generic readers must follow the new native project; historical mutation scripts retain their guards.
for name in ['read-pcb-source-v13.js','read-pcb-pads-v13.js','check-pcb-v13.js']:
 p=R/'scripts'/name;s=p.read_text(encoding='utf8');p.write_text(s.replace('de280d363d1bdc6eb48b4e11624beec0d326c823aa88a60393f490d052ff1c05',pid['uuid']),encoding='utf8')
old=D/'V0.13-ML307R引脚边界与封装复核记录.md';s=old.read_text(encoding='utf8');old.write_text('> 更新：本项已在ML307fix版完成模型和焊盘修正，并适配周边RF/USB布局。见《V0.13-ML307R专用封装修正记录.md》。下文保留修复前核对历史；厂家DFM仍待新资料复查。\n\n'+s,encoding='utf8')
print(json.dumps({'project':str(items[0]),'gerber':str(items[1]),'archive':str(package),'backup':backup,'PCB_DRC':0,'factoryDfmPassed':False},ensure_ascii=True))
