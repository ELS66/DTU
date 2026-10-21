from pathlib import Path
import json,zipfile,hashlib,shutil,csv,math
R=Path('PCB');M=R/'manifests';E=R/'eda';D=R/'docs'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2),encoding='utf8')
n=load(M/'clearancefix-native-verification-v14.json');g=load(M/'clearancefix-manufacturing-verification-v14.json');fp=load(M/'clearancefix-footprint-audit-v14.json');stage=load(M/'clearancefix-stage-v14.json');proj=load(M/'clearancefix-project-id-v14.json');screen=load(M/'clearancefix-all-pin-model-screen-v14.json')
assert n['nativeReopenedDrcIssues']==0 and n['defaultAssembly']==99 and n['boardMm']==[60,75]
assert fp['copperContainsNominalLeadCount']==109 and fp['pasteAperturesMatchOriginalNominalCount']==109
assert g['minimumMovedViaAnnulusToMaskGapMm']>=.15 and g['drillCount']==326
readme=E/'DTU-V0.14-Clearancefix-README.md';doc=D/'V0.14-封装边界与模组净空修正记录.md'
readme.write_text('''# DTU V0.14 · 60×75 mm · 四层 · 单面贴装

日期：2026-10-16。基线：V0.13 ML307fix。此包是工程复查版；尚未取得新版嘉立创 DFM 验收结果。

本版将两颗模组与左右六个状态灯上移 2 mm，上方天线和下载口等器件上移 3.2 mm；板高由70改为75 mm，顶端安装孔随板框上移5 mm。底部三个 HY2.0 立贴4P端子座的位置、针序和净空区保持原样。默认仍为99件实装，5个DNP；器件总数104，均在正面。过孔310个，比基线增加2个；总钻孔326个。

ML307R 的109个焊盘各边增加0.05 mm标称铜面余量。外围铜焊盘为2.70×0.70 mm、R0.05；内焊盘为1.10×0.80 mm、中心六个为1.40×1.40 mm。此为工程适配封装，依据手册重建，含工程调整。物理焊脚模型保留，锡膏开口仍采用原标称尺寸：外围2.60×0.60 mm圆端，内侧1.00×0.70 mm，中心1.30×1.30 mm。

已核对实际导出的109个铜焊盘、109个锡膏开口，最小标称焊脚铜面余量约0.050 mm；ML307R最近器件外形间距约3.125 mm；原生PCB DRC为0。已修正移动后的过孔间距、状态灯连接、局部阻焊间距及SIM座旁一颗历史接地过孔。

请将本包中的 Gerber、BOM、CPL 一起用于新版DFM复查。旧V0.13文件保留供追溯。工程已命名为“DTU-V0.14-ML307R-DL-单面贴装-60x75”。

检查记录列出了仍需复核的装配模型疑点，包括SIM座、天线座及部分指示灯；它们来自本地模型粗筛和历史DFM截图，尚未得到新版工厂DFM的结论。50 Ω射频、90 Ω USB还需根据实际生产叠层核算，尚未做阻抗或硬件实测。PCB DRC为0不能作为整板生产签核。
''',encoding='utf8')
pending={
 'revision':'V0.14','factoryDfmPassed':False,
 'localNominalModelScreen':screen,
 'historicalFactoryScreensToRecheck':[
  {'item':'J1/J2/J3同位号自碰撞','status':'待新版DFM和模型识别复核；实装器件外形间无重叠，未将截图中的9项直接判为误报。'},
  {'item':'C53/J4、C57/J4、Q1/C85、Q1/U1、J4/C94装配余量','status':'历史0.09表示模型放大比例；保留工厂装配复核项。'},
  {'item':'少量历史同网络焊盘/过孔距离提示','status':'须按新版具体对象、铜面和阻焊开窗复查，未将原生DRC通过当作工厂DFM通过。'}],
 'engineeringLimits':['ML307R新增0.05mm为标称几何余量，未完成器件公差、贴装偏差、钢网厚度与回流工艺的联合验证。','RF和USB阻抗需根据实际生产叠层核算。','尚无本版硬件实测与新版嘉立创DFM完整报告。']}
save(M/'clearancefix-dfm-pending-items-v14.json',pending)
doc.write_text(f'''# V0.14 封装边界与模组净空修正记录

日期：2026-10-16。修订基线与文件校验值见本包清单。修改前备份：`{stage['backupDirectory']}`。

## 修改及原因

V0.13按手册圆端焊盘重建后，矩形焊脚模型的内侧角仍有标称越界；48个外围区域最大约0.1243 mm。同时部分邻近器件不足手册要求的3 mm距离。

本版采用工程铜焊盘适配：109个焊盘的长、宽各增加0.10 mm，各边提供0.05 mm标称余量；外围拐角R0.05。48个外围锡膏开口通过封装内独立顶层锡膏图形保留原圆端形状，61个内侧开口通过收缩铜焊盘开口保留原尺寸。封装中的上下锡膏扩展值成对保存，已通过重新导入与实际Gerber导出验证，避免只改运行时状态而在重新打开后丢失设置。

封装名称为 `DTU_ML307R_DL_109_ENGINEERING_MARGIN_V14`。此为工程适配封装。物理模型、引脚编号、网络映射及原理图电气内容均保持。依据为 [ML307R硬件手册 Figure19/20，印刷页55/56](https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1189/M307R_Hardware_Datasheet.pdf)。原图页随复查包提供。

板框由60×70改为60×75 mm。两颗模组及六个侧边状态灯上移2 mm，两颗模组保持顶边对齐、ESP在右、ML307R在左；上方天线与下载口等15个器件上移3.2 mm。最近模组邻件为R64，外形距离{n['U2MinimumNominalBodyGapMm']:.4f} mm。默认99件实装器件外形粗检无小于0.3 mm的邻件间距。外形检查使用库中标称轮廓，未包含实物最大公差。

顶端两个安装孔移至(4,71)、(56,71) mm；底部孔仍为(4,4)、(56,4) mm，均Ø3.2 mm NPTH。三个下沿HY2.0端子座位置、针序和下沿净空不变。仅保留端子旁15个丝印文字，实际丝印几何与基线一致。

移动后的布线重新接通；4G原0.8 mm支路宽度保持；去掉一颗重叠接地过孔。另将SIM座GND过孔从(20.675,24.975)移到(20.525,24.975) mm，拉开阻焊和焊脚附近的距离。最终310个过孔、326个钻孔，较基线增加2个过孔。导入时软件删除一条端点重合的零长度USB线段，原生连通检查通过，已记录到原生复核JSON。

## 已取得的验证结果

|检查|结果|
|---|---|
|原生PCB DRC|0|
|实际源文件与布线计划|一致；515条走线、310个过孔|
|ML307R标称焊脚铜面包含关系|109/109；最小余量{fp['minimumNominalLeadCopperMarginMm']:.5f} mm|
|ML307R实际锡膏开口与原标称尺寸|109/109一致|
|ML307R周边最小标称外形距离|{n['U2MinimumNominalBodyGapMm']:.4f} mm|
|全板最小钻孔壁间距|{g['minimumDrillWallGapMm']:.4f} mm|
|丝印至钻孔壁最小间距|{g['silkToDrillWallMinimumGapMm']:.4f} mm|
|丝印至阻焊开窗最小间距|{g['silkToMaskMinimumGapMm']:.4f} mm|
|移动/新增过孔焊环至顶层开窗最小间距|{g['minimumMovedViaAnnulusToMaskGapMm']:.4f} mm|
|射频信号换层|全在顶层，无射频信号过孔；既有0.35 mm线宽保持|
|实装BOM/CPL|99个位号一致，正面贴装|

Gerber复查包含12个制造文件。保留对原生导出数值残留的校验清理：移除安装孔处16个零尺寸铜占位闪点和2个极小的盖油过孔阻焊数值残留，未删除实际过孔铜环或钻孔。

几何辅助检查采用0.1528 mm阈值时，原有TTL_RX_EXT与VDD_3V3的两对线段仍为约0.151961 mm；这两对位于未改动区域，原生DRC通过。其原始检查结果附在包内，未计作辅助检查“全部为零”。

## 仍需落实的复核

本版尚无新版嘉立创DFM报告，工厂级DFM通过状态为false。本地标称模型粗筛发现18个待核对区域：SIM座J4七个、U.FL天线座J5一个、部分指示灯十个。粗筛使用库中第50层焊脚图形和SDK焊盘几何，未替代厂家焊接区定义及DFM三维模型判断；这些区域没有通过删除模型或随意扩大连接器焊盘来消除。原始对象和面积见“装配模型待核实.json”。

历史端子座同位号自碰撞和装配余量提示仍须以新版DFM复查。射频/USB阻抗、元器件与贴装公差、钢网厚度、回流工艺和硬件功能均尚未完成生产签核。此文件记录本次已完成的工程修正及验证范围。
''',encoding='utf8')
files=[E/'DTU-V0.14-60x75-Clearancefix.epro2',E/'DTU-V0.14-60x75-Clearancefix-Gerber.zip',E/'DTU-V0.14-Clearancefix-BOM-99.csv',E/'DTU-V0.14-Clearancefix-CPL-99-Top.csv',readme,doc,E/'DTU-V0.14-Clearancefix-preview.png',E/'DTU-V0.14-Clearancefix-ML307-detail.png']
manifest={'revision':'V0.14 封装边界与模组净空修正 2026-10-16','boardMm':[60,75],'layers':4,'assembly':'Top','components':104,'defaultAssembly':99,'vias':310,'drilledHoles':326,'pcbDrcIssues':0,'factoryDfmPassed':False,'backupDirectory':stage['backupDirectory'],'projectUuid':proj['uuid'],'pcbUuid':proj['pcb'],'nativeProject':str(files[0].resolve()),'productionGerber':str(files[1].resolve()),'deliveryArchive':str((E/'DTU-V0.14-60x75-DFM复查包.zip').resolve()),'actualCopperManifest':'clearancefix-actual-routing-v14.json','actualSourceSnapshot':'clearancefix-final-source-v14.json','files':[{'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
save(M/'current-pcb-delivery-v14.json',manifest)
bundle=Path(manifest['deliveryArchive'])
checks={'原生检查.json':M/'clearancefix-native-verification-v14.json','制造文件检查.json':M/'clearancefix-manufacturing-verification-v14.json','ML307R焊盘与钢网检查.json':M/'clearancefix-footprint-audit-v14.json','装配模型待核实.json':M/'clearancefix-dfm-pending-items-v14.json','辅助铜间距检查.json':M/'clearancefix-actual-copper-check-v14.json','版本清单.json':M/'current-pcb-delivery-v14.json'}
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,p.name)
 for name,p in checks.items():z.write(p,name)
 for page in [55,56]:
  p=R/f'references/ML307R-hardware-page-{page}.png';z.write(p,'参考图/'+p.name)
with zipfile.ZipFile(bundle) as z:
 assert z.testzip() is None
 for p in files:assert z.read(p.name)==p.read_bytes()
save(M/'current-pcb-delivery-v13.json',manifest) # Existing tooling reads this historical manifest filename.
save(M/'current-pcb-delivery.json',manifest)
for source,name in [(files[0],'DTU-current.epro2'),(files[1],'DTU-current-Gerber.zip'),(files[2],'DTU-current-BOM.csv'),(files[3],'DTU-current-CPL-Top.csv'),(bundle,'DTU-current-review.zip')]:shutil.copy2(source,E/name)
(E/'当前版本说明.md').write_text('当前版本：V0.14，60×75 mm，四层、单面贴装。\n\n请使用 DTU-V0.14-60x75-DFM复查包.zip 或 DTU-current-review.zip 整包复查。旧V0.13文件保留追溯，其文件名带“DFM-review”或“验收资料包”也不代表当前版本。工程复查结果和未完成事项见包内记录；尚未取得新版嘉立创DFM验收结果。\n',encoding='utf8')
old='c2bff6216166854806fb0135bb156a18c0ae8c03a227bd251e55df64cd0baefb'
for name in ['read-pcb-source-v13.js','read-pcb-pads-v13.js','check-pcb-v13.js']:
 p=R/'scripts'/name;p.write_text(p.read_text(encoding='utf8').replace(old,proj['uuid']),encoding='utf8')
print('Packaged',bundle,'bytes',bundle.stat().st_size,'native project',proj['uuid'])
