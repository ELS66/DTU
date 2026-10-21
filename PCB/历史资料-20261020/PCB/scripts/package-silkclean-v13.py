"""Verify native silk cleanup, preserve production copper, package revision."""
from pathlib import Path
import json,zipfile,collections,math,hashlib,shutil,csv,io

R=Path('PCB');E=R/'eda';M=R/'manifests';D=R/'docs'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
def rows(source):
    out={}
    for line in source.splitlines():
        if '||' not in line:continue
        h,b=line.split('||',1);h=json.loads(h)
        if h['type']!='DOCHEAD':out[(h['type'],h.get('id',''))]=json.loads(b.removesuffix('|'))
    return out
before=rows(load(M/'silk-clean-before-v13.json')['result']['source'])
after=rows(load(M/'silkclean-reopened-source-v13.json')['result']['source'])
assert after==rows(load(M/'silkclean-native-source-v13.json')['result']['source'])
changed=[k for k in before.keys()|after.keys() if before.get(k)!=after.get(k)]
assert len(changed)==27 and all(k[0]=='STRING' for k in changed)
texts=[(k,b) for k,b in after.items() if k[0]=='STRING'];assert len(texts)==15
for k,b in texts:
    assert b['layerId']==3 and abs(b['fontSize']*.0254-1.8)<.00001
    assert abs(b['strokeWidth']*.0254-.15)<.00001
    a=before[k];assert abs((b['y']-a['y'])*.0254+.2)<.00001
    assert all(a.get(v)==b.get(v) for v in a.keys()|b.keys() if v not in ['y','fontSize'])
assert load(M/'silkclean-pcb-drc-v13.json')['result']==[]

def active_project(file):
    with zipfile.ZipFile(file) as z:
        source=z.read(next(n for n in z.namelist() if n.endswith('.epru'))).decode('utf8')
    doc=None;out={}
    for line in source.splitlines():
        if '||' not in line:continue
        h,b=line.split('||',1);h=json.loads(h)
        try:b=json.loads(b.removesuffix('|'))
        except ValueError:b=None
        if h['type']=='DOCHEAD':doc=(b['docType'],b['uuid']);continue
        k=(*doc,h['type'],h.get('id',''))
        if b is None:out.pop(k,None)
        else:out[k]=b
    return out
oldproj=active_project(E/'DTU-V0.13-60x70-Exposurefix.epro2')
newproj=active_project(E/'DTU-V0.13-60x70-Silkclean.epro2')
full_changes=[k for k in oldproj.keys()|newproj.keys() if oldproj.get(k)!=newproj.get(k)]
metadata_changes=[]
for k in full_changes:
    a,b=oldproj.get(k),newproj.get(k)
    if k[0]=='FOOTPRINT' and k[2]=='ELE_PLACEHOLDER':metadata_changes.append(k);continue
    if k[0]=='BLOB' and a=={} and b is None:metadata_changes.append(k);continue
    assert k[0] in ['PCB','FOOTPRINT'] and isinstance(a,dict) and a.get('layerId') in [3,4],k
for k,b in newproj.items():
    if k[0]=='FOOTPRINT' and isinstance(b,dict) and b.get('layerId') in [3,4]:
        assert k[2] in ['LAYER','ATTR'],k
        if k[2]=='ATTR':assert not b.get('keyVisible') and not b.get('valueVisible')

exec((R/'scripts/render-hy20-gerber-v13.py').read_text(encoding='utf8').split('for label,copper,mask,silk in')[0])
z.close();raw=zipfile.ZipFile(E/'DTU-V0.13-60x70-Silkclean-Gerber-raw')
old=zipfile.ZipFile(E/'DTU-V0.13-60x70-Exposurefix-Gerber.zip')
z=raw;cache.clear();names=old.namelist();silk_names=['Gerber_TopSilkscreenLayer.GTO','Gerber_BottomSilkscreenLayer.GBO']
native={n:geom(n)[0] for n in names if not n.endswith('.DRL')}
native_drills={n:drill(n) for n in names if n.endswith('.DRL')}
mounts=[q for q in native_drills['Drill_NPTH_Through.DRL'] if q[2]>3]
assert len(mounts)==4
z=old;cache.clear()
from shapely.strtree import STRtree
def printable_features(name,features):
    out=[]
    for g,d in features:
        if name in ['Gerber_TopLayer.GTL','Gerber_BottomLayer.GBL','Gerber_InnerLayer1.G1','Gerber_InnerLayer2.G2'] and g.area<.0000011 and any(g.centroid.distance(Point(q[:2]))<.002 for q in mounts):continue
        if 'SolderMask' in name and g.area<1e-10:continue
        out.append((g,d))
    return out
preserved=[]
for name,features in native.items():
    if name in silk_names:continue
    previous=geom(name)[0];features=printable_features(name,features);assert len(features)==len(previous),(name,len(features),len(previous))
    index=STRtree([g for g,d in previous]);used=set()
    for g,d in features:
        matches=[int(i) for i in index.query(g.representative_point().buffer(.00002)) if int(i) not in used and previous[i][1]==d and max(abs(x-y) for x,y in zip(g.bounds,previous[i][0].bounds))<.00001 and g.hausdorff_distance(previous[i][0])<.00001]
        assert matches,(name,g.bounds)
        used.add(matches[0])
    preserved.append(name)
for name,holes in native_drills.items():
    remaining=drill(name);assert len(remaining)==len(holes)
    for q in holes:
        i=min(range(len(remaining)),key=lambda i:max(abs(a-b) for a,b in zip(q,remaining[i])))
        assert max(abs(a-b) for a,b in zip(q,remaining[i]))<.00001
        remaining.pop(i)
production=E/'DTU-V0.13-60x70-Silkclean-Gerber.zip'
with zipfile.ZipFile(production,'w',zipfile.ZIP_DEFLATED) as q:
    for name in names:q.writestr(name,raw.read(name) if name in silk_names else old.read(name))
assert all(old.read(n)==zipfile.ZipFile(production).read(n) for n in names if n not in silk_names)
silk=unary_union([g for g,d in native['Gerber_TopSilkscreenLayer.GTO'] if d])
mask=unary_union([g for g,d in geom('Gerber_TopSolderMaskLayer.GTS')[0] if d])
gap=silk.distance(mask);assert gap>.18 and not native['Gerber_BottomSilkscreenLayer.GBO']
assert all(g.bounds[1]>8 and g.bounds[3]<12 for g,d in native['Gerber_TopSilkscreenLayer.GTO'])
raw.close();old.close()
native_cpl={q['Designator']:q for q in csv.DictReader(io.StringIO((E/'DTU-V0.13-Silkclean-CPL-native').read_text(encoding='utf-16')),delimiter='\t')}
prior_cpl=list(csv.DictReader((E/'DTU-V0.13-Exposurefix-CPL-99-Top.csv').open(encoding='utf-8-sig')))
for q in prior_cpl:
    n=native_cpl[q['Designator']]
    assert all(abs(float(q[f].removesuffix('mm'))-float(n[f].removesuffix('mm')))<.00001 for f in ['Mid X','Mid Y'])
    assert (float(q['Rotation'])-float(n['Rotation']))%360<.00001
for suffix in ['BOM-99.csv','CPL-99-Top.csv']:shutil.copy2(E/f'DTU-V0.13-Exposurefix-{suffix}',E/f'DTU-V0.13-Silkclean-{suffix}')
verification={'PCB_DRC':0,'factoryDfmPassed':False,'reopenedNativeSourceVerified':True,'keptTextObjects':15,'keptTerminalNames':['RS485','RS232','UART'],'keptPinLabels':['P A B G','P T R G','P T R G'],'nominalTextSizeMm':1.8,'strokeWidthMm':.15,'textMoveYmm':-.2,'silkToMaskMinimumGapMm':gap,'geometryComparisonToleranceMm':.00001,'unchangedProductionNonSilkFilesByBytes':[n for n in names if n not in silk_names],'nativeNonSilkGeometryCompared':preserved,'componentAndPadGeometryUnchanged':True,'BOMandCPLUnchanged':True,'normalizedImportMetadataCount':len(metadata_changes),'removedFootprintGraphics':529,'removedDownloadTextObjects':12,'newProjectUuid':'de280d363d1bdc6eb48b4e11624beec0d326c823aa88a60393f490d052ff1c05','PCB': '4211128ecf040c100b33238447713203'}
save(M/'silkclean-manufacturing-verification-v13.json',verification)

guide=D/'V0.13-精简丝印版接口说明.md'
guide.write_text('''# V0.13 精简丝印版接口说明

按元件面观察，底部端子从左到右为 J1/RS485、J2/RS232、J3/UART。各端子从左到右针序如下。

| 接口 | 第1脚 | 第2脚 | 第3脚 | 第4脚 |
|---|---|---|---|---|
| J1 RS485 | P：VIN_IN | A：RS485_A_EXT | B：RS485_B_EXT | G：GND |
| J2 RS232 | P：VIN_IN | T：RS232_TX_EXT | R：RS232_RX_EXT | G：GND |
| J3 UART | P：VIN_IN | T：TTL_TX_EXT | R：TTL_RX_EXT | G：GND |

顶部两组下载孔仍保留裸孔，默认不装不焊。本版移除了板面的下载文字。元件面观察，左组为 J7/LTE，右组为 J6/ESP；每组从左到右，第1孔为方焊盘。

| 下载组 | 第1孔 | 第2孔 | 第3孔 | 第4孔 | 第5孔 |
|---|---|---|---|---|---|
| J7 LTE | GND | LTE_USB_DP_EXT | LTE_USB_DM_EXT | LTE_USB_VBUS | LTE_BOOT_FIXTURE |
| J6 ESP | GND | ESP_USB_DP_EXT | ESP_USB_DM_EXT | ESP_EN | ESP_BOOT |

以上为当前网表针序，不能仅凭字母 P/VB 将电源接入任意电压。电源接法与下载时序沿用原理图及已确定方案。

去除丝印不会切断铜线，也不会改变元件电气极性；但电解电容、二极管、LED、芯片第1脚等板面提示已删除。手工装配和维修时应对照原理图、BOM、CPL、封装焊盘编号及厂商极性定义，不能仅凭精简版板面判断。元件型号、编号、管脚网络和装配坐标仍在工程及装配资料中，修改前完整工程也已备份。
''',encoding='utf8')
backup=load(M/'silk-clean-backup-v13.json')['directory']
report=D/'V0.13-丝印精简修正记录.md'
report.write_text(f'''# V0.13 丝印精简修正记录

2026-10-16。依据用户“只保留端子座边上的丝印”要求，本版 Silkclean 去除封装自带边框、引脚/极性点、下载孔外框等非必要丝印，并去除顶部两组下载口的 12 个文字对象。保留底部 RS485、RS232、UART 及 PABG/PTRG/PTRG，共 15 个独立文本对象。主问题来自封装图形压到开窗，不能把截图上千项计数理解为上千个文字。

保留文字的名义字号增至 1.8 mm、笔画宽约 0.15 mm，整组向下移动 0.20 mm。生产 Gerber 丝印至阻焊开窗最小距离为 {gap:.6f} mm，高于截图“丝印距焊盘”良好阈值 0.18 mm。顶层只有底部三个端子文字区域，背面丝印为空。

此次在可编辑工程中一并清理了 60 个封装文档上的共 529 个丝印图形记录（其中包含未实装/历史封装，实际 PCB 使用 32 种封装）；不删除封装绑定、引脚号、焊盘、48 层元件外形或三维模型。为使封装及 PCB 内部缓存一致，导入为本地精简版工程副本并已在嘉立创EDA打开。项目 UUID 为 de280d363d1bdc6eb48b4e11624beec0d326c823aa88a60393f490d052ff1c05，PCB UUID 不变；工程存放目录为 PCB/native-Silkclean。旧工程和修改前交付文件保留。

验证：清理版已保存、关闭、重新打开，15 个文字的字号与位置仍保留；原生 PCB DRC=0。PCB 源码与修改前逐项比对，变化只涉及 27 个 STRING：12 个删除、15 个调整字号和 Y 坐标；全部铜图元、网表绑定、器件位置、焊盘、过孔和规则不变。整套工程的非丝印图形数据也逐项比对，除导入器重排的元件 ID 分配计数及删除一个空 BLOB 元数据外未发现其他变化。

本版非丝印 Gerber 与前一 Exposurefix 版先进行原生导出几何比对（0.00001 mm 容差，排除已确认的安装孔占位与盖油数值残点），再逐文件按原始字节原样保留；正式 ZIP 仅替换顶/底丝印文件。因而四层铜、阻焊、钢网、钻孔和板框与前一生产 ZIP 完全一致。既有四角无铜安装孔、R36 阻焊桥、两处接地过孔移位修正均保留。BOM/CPL 经原生新导出核对后原样复制，99 件装配坐标与方向不变。

规格仍为 60×70 mm、四层、单面贴装、104 个封装/99 件实装、306 个过孔、322 个钻孔。本次不宣称整板厂家 DFM 通过，仍需用新 ZIP 重跑“丝印距焊盘”和相关字体检查；其他既有工艺待确认项继续保留。

去除丝印不改变电路功能，主要影响手工识别、装配极性判断和维修查找。原理图、BOM、CPL 与脚号仍保留，端子针序仍印在板面；下载接口针序另见《V0.13-精简丝印版接口说明.md》。

备份：{backup}。生产文件：DTU-V0.13-60x70-Silkclean-Gerber.zip。工程：DTU-V0.13-60x70-Silkclean.epro2。后续继续编辑时打开 Silkclean 工程副本；直接从旧工程重新导出会重新带出旧丝印。
''',encoding='utf8')
readme=E/'DTU-V0.13-Silkclean-README.md'
readme.write_text('''# V0.13 丝印精简复查版

当前 Silkclean 版仅保留底部三个端子的名称与针序。最小丝印至阻焊间距约 0.289 mm；PCB DRC=0，整板厂家 DFM 尚未完成。

使用 Silkclean-Gerber.zip 重跑 DFM；可编辑工程为 Silkclean.epro2，本地清理副本已在EDA打开（PCB/native-Silkclean）。不要从旧工程重新导出旧丝印。

BOM/CPL 与 Exposurefix 版完全一致，复制为本版名称配套交付。铜层、阻焊、钢网、钻孔、板框等非丝印生产文件与 Exposurefix 原样一致。保留四角无铜孔及此前布线修正。

板面极性点和下载文字已移除；装配与维修对照原理图/BOM/CPL及封装引脚定义，顶部裸孔针序见接口说明。J6/J7仍默认不装不焊。
''',encoding='utf8')
items=[E/'DTU-V0.13-60x70-Silkclean.epro2',production,E/'DTU-V0.13-Silkclean-BOM-99.csv',E/'DTU-V0.13-Silkclean-CPL-99-Top.csv',guide,report,readme]
package=E/'DTU-V0.13-60x70-丝印精简复查包.zip'
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as q:
    for p in items:q.write(p,p.name)
for p in [production,package,items[0]]:
    with zipfile.ZipFile(p) as q:assert q.testzip() is None
current=load(M/'current-pcb-delivery-v13.json')
current.update({'revision':'V0.13 丝印精简 2026-10-16','status':'仅保留三组端子文字，待厂家DFM重新检查丝印','projectUuid':verification['newProjectUuid'],'pcbUuid':verification['PCB'],'nativeWorkspaceDirectory':str((R/'native-Silkclean').resolve()),'nativeProject':str(items[0].resolve()),'productionGerber':str(production.resolve()),'deliveryArchive':str(package.resolve()),'actualSourceSnapshot':'silkclean-reopened-source-v13.json','actualPadManifest':'silkclean-pcb-pads-v13.json','backupDirectory':backup,'silkscreenReview':str(report.resolve()),'interfaceGuide':str(guide.resolve()),'files':[{'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in items]})
current['openDfmItems']=[s for s in current['openDfmItems'] if not s.startswith('丝印')]+['丝印：已仅保留三组端子文字，最小开窗避让约0.289mm，待新资料重跑DFM确认。']
save(M/'current-pcb-delivery-v13.json',current)
shutil.copy2(M/'silkclean-pcb-drc-v13.json',M/'check-pcb-v13.json')
for a,b in [('DTU-V0.13-60x70-Silkclean.epro2','DTU-V0.13-60x70-DFM-review.epro2'),('DTU-V0.13-60x70-Silkclean-Gerber.zip','DTU-V0.13-60x70-SMT-4L-Gerber-DFM.zip'),('DTU-V0.13-60x70-丝印精简复查包.zip','DTU-V0.13-60x70-验收资料包.zip'),('DTU-V0.13-Silkclean-README.md','DTU-V0.13-README.md')]:shutil.copy2(E/a,E/b)
print(json.dumps(verification,ensure_ascii=True))
