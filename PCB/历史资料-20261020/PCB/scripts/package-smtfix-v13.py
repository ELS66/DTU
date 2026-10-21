from pathlib import Path
import json,csv,io,zipfile,shutil,collections,math
P=Path('PCB');E=P/'eda';M=P/'manifests';D=P/'docs'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
assert load(M/'smt-fixed-pcb-drc-v13.json')['result']==[]
assert not load(M/'smt-fixed-body-audit-v13.json')['bodyOverlaps']
assert not load(M/'smt-fixed-body-audit-v13.json')['uniform5PercentExpansionIntersections']
assert not load(M/'smt-rerouted-copper-check-v13.json')['conflicts']
src=load(M/'source-after-smt-fix-v13.json')['result']['source'];plan={'routes':[],'vias':[]}
for l in src.splitlines():
 if '||' not in l:continue
 h,b=l.split('||',1);h=json.loads(h);b=json.loads(b.removesuffix('|'))
 if h['type']=='VIA':plan['vias'].append({'id':h['id'],'net':b['netName'],'x':b['centerX']*.0254,'y':b['centerY']*.0254,'diameter':b['viaDiameter']*.0254,'hole':b['holeDiameter']*.0254})
 if h['type']=='POLY' and b['layerId'] in [1,2,15,16] and b['netName']:
  assert all(not isinstance(v,str) or v=='L' for v in b['path'])
  v=[v*.0254 for v in b['path'] if isinstance(v,(int,float))]
  plan['routes'].append({'id':h['id'],'net':b['netName'],'layer':b['layerId'],'widthMm':b['width']*.0254,'pointsMm':list(map(list,zip(v[::2],v[1::2])))})
expected=load(M/'smt-rerouted-plan-v13.json')
def rs(r):return (r['net'],r['layer'],round(r['widthMm'],4),tuple(round(v,4) for q in r['pointsMm'] for v in q))
def vs(v):return(v['net'],round(v['x'],4),round(v['y'],4))
assert collections.Counter(map(rs,plan['routes']))==collections.Counter(map(rs,expected['routes']))
assert collections.Counter(map(vs,plan['vias']))==collections.Counter(map(vs,expected['vias']))
assert len(plan['vias'])==306
save(M/'smt-fixed-actual-routing-v13.json',plan)
exec((P/'scripts/render-hy20-gerber-v13.py').read_text(encoding='utf8').split('for label,copper,mask,silk in')[0].replace('HY20','SMTfix'))
holesBy={n:drill('Drill_'+n+'_Through.DRL') for n in ['PTH','NPTH']};hs=holesBy['PTH']+holesBy['NPTH']
assert len(hs)==322 and len(holesBy['PTH'])==316 and len(holesBy['NPTH'])==6
gap=min(math.dist(a[:2],b[:2])-(a[2]+b[2])/2 for i,a in enumerate(hs) for b in hs[:i])
mask=unary_union([g for g,d in geom('Gerber_TopSolderMaskLayer.GTS')[0] if d]);silk=unary_union([g for g,d in geom('Gerber_TopSilkscreenLayer.GTO')[0] if d]);silkgap=mask.distance(silk)
assert gap>.25 and silkgap>.15
files=['Gerber_TopLayer.GTL','Gerber_BottomLayer.GBL','Gerber_InnerLayer1.G1','Gerber_InnerLayer2.G2','Gerber_TopSilkscreenLayer.GTO','Gerber_BottomSilkscreenLayer.GBO','Gerber_TopSolderMaskLayer.GTS','Gerber_BottomSolderMaskLayer.GBS','Gerber_TopPasteMaskLayer.GTP','Gerber_BoardOutlineLayer.GKO','Drill_PTH_Through.DRL','Drill_NPTH_Through.DRL']
assert 'Gerber_BottomPasteMaskLayer.GBP' not in z.namelist()
gerber=E/'DTU-V0.13-60x70-SMTfix-Gerber.zip'
with zipfile.ZipFile(gerber,'w',zipfile.ZIP_DEFLATED) as o:
 for n in files:o.writestr(n,z.read(n))
save(M/'smt-fixed-manufacturing-check-v13.json',{'holes':len(hs),'vias':len(plan['vias']),'drillDiameters':dict(collections.Counter(round(v[2],3) for v in hs)),'minimumDrillWallGapMm':gap,'silkToMaskClearanceMm':silkgap,'pcbDrcIssues':0,'factoryDfmPassed':False,'openDfmItems':['same-reference connector model collision warnings','remaining PCB/SMT categories not yet supplied']})
native=list(csv.DictReader(io.StringIO((E/'DTU-V0.13-SMTfix-CPL-native').read_text(encoding='utf-16')),delimiter='\t'));dnp={'C50','C51','R32','J6','J7'}
cpl=[{'Designator':r['Designator'],'Mid X':r['Mid X'],'Mid Y':r['Mid Y'],'Layer':'Top','Rotation':r['Rotation']} for r in native if r['Designator'] not in dnp]
assert len(cpl)==99 and all(r['Layer']=='T' for r in native)
with (E/'DTU-V0.13-SMTfix-CPL-99-Top.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(cpl[0]));w.writeheader();w.writerows(cpl)
shutil.copy2(E/'DTU-V0.13-HY20-BOM-99.csv',E/'DTU-V0.13-SMTfix-BOM-99.csv')
assert {r['Designator'] for r in cpl}=={r['Designator'] for r in csv.DictReader((E/'DTU-V0.13-SMTfix-BOM-99.csv').open(encoding='utf-8-sig'))}
report='''# V0.13 SMT 碰撞问题复核与局部修正

2026-10-15。用户提交嘉立创 DFM 截图后复核。状态：两处已确认的布局问题已修正，原生 PCB DRC=0，整套厂家 DFM 尚未闭环。

## 已确认的问题

第一张截图为“元件碰撞预警”，数值 0.05 按截图说明表示将模型放大 5% 后发生碰撞，不是测量间距 0.05 mm。侧栏显示 11 个危险、5 个警告、8 个良好结果；当前截图未展示全部明细，不能将其全部认定为真实碰撞或误报。

- D6 / U7：按库元件外形层（48 层）变换到实际 PCB 坐标，本体相交面积约 1.105 mm²。此前只检查焊盘铜皮，未覆盖本体，属于检查遗漏。
- U1 / Q1：库本体间隙约 0.325 mm，放大 5% 后相交，装配余量不足。
- J2/J2、J3/J3：当前工程每个位号仅一个实例，未发现重复放置。三个端子本体互不相交，但同位号提示的模型匹配/内部几何原因尚未确认，不能直接忽略。

## 已落实的修改

- D6 从 (26.75,19.50) 移至 (28.00,12.10) mm，方向保持 180°，靠近下方 RS232 接口区；未进入三个底座之间或底座下方。重新连接信号，并增设附近专用接地过孔，避免沿用远处接地点的长回路。
- Q1 从 (28.50,42.00) 移至 (28.00,42.00) mm，方向保持 0°；与 ESP32 本体间隙增至约 0.825 mm，重新整理六脚引线。
- 其他 102 个器件位置未改，三个 HY2.0 座及其焊盘未改，电路逐针网络未改。104 个封装、99 件默认实装、全部 Top，板框仍 60×70 mm、四层。
- 过孔 304→306，总钻孔 320→322；增加的两个孔分别用于 TVS 就近接地和信号换层。未为降低告警数量取消必要连接。
- 三个现场接口的名称/针序整排向下移 1.5 mm，避免新 D6 焊盘与 RS232 文字相交；仍只保留接口文字。实际 Gerber 丝印到阻焊开窗最小约 0.526 mm。

## 已验证与限制

重建原生铺铜后，PCB DRC=0；104 件逐针网表一致。当前库本体几何检查无实际相交、无放大 5% 后相交；非铺铜铜皮复核 0 冲突，最小间距约 0.157 mm。此项不是嘉立创 DFM 的完整 3D 检查，也不代表所有 6%～10% 装配余量警告已经消除。

前一交付 Gerber 的全部 304 个过孔已额外逐层检查：四个铜层均具有完整过孔铜环，未复现缺少铜环。第二张图主要展示孔/底面效果，不能单凭该图认定焊盘缺失。第三张为装配预览，也不能替代线路、阻焊、钻孔等 PCB 加工检查明细。

仍需以本版 Gerber+BOM+CPL 重新运行 DFM，并继续提供 PCB结果列表、剩余 SMT 分类及一条同位号端子告警的定位图。未确定 PDF 导出失败原因；未修改 DFM 报警阈值或屏蔽规则。

## 资料对应

- 修改前备份：`PCB/backups/20261015-before-SMT-collision-fix-154620/`。
- 当前工程：`DTU-V0.13-60x70-SMTfix.epro2`。
- 复查 Gerber：`DTU-V0.13-60x70-SMTfix-Gerber.zip`。
- 装配：`DTU-V0.13-SMTfix-BOM-99.csv`、`DTU-V0.13-SMTfix-CPL-99-Top.csv`。
- 原 HY20 专用文件保留作历史，位置与本次不同，请勿混用旧 CPL。
'''
(D/'V0.13-SMT碰撞复核与修正记录.md').write_text(report,encoding='utf8')
readme='''# V0.13 SMT 碰撞局部修正复查包

这是 DFM 复查版，尚未完成全部厂家 DFM 验收，不作为量产放行包。

导入本包 SMTfix-Gerber.zip；需要装配检查时，同时使用 SMTfix-BOM-99.csv 与 SMTfix-CPL-99-Top.csv。三个文件来自同一版，请勿混用旧 HY20 坐标。

两处已确认问题：D6/U7 本体重叠、U1/Q1 装配余量不足，均已调整。原生 PCB DRC=0，库本体及其放大5%几何无相交。其他 DFM 告警仍按实际结果逐项复查，详见包内修正记录。
'''
(E/'DTU-V0.13-SMTfix-README.md').write_text(readme,encoding='utf8')
package=E/'DTU-V0.13-60x70-SMT碰撞修正复查包.zip'
items=[E/'DTU-V0.13-60x70-SMTfix.epro2',gerber,E/'DTU-V0.13-SMTfix-BOM-99.csv',E/'DTU-V0.13-SMTfix-CPL-99-Top.csv',D/'V0.13-SMT碰撞复核与修正记录.md',E/'DTU-V0.13-SMTfix-README.md',E/'DTU-V0.13-SMTfix-Gerber-top.png',E/'DTU-V0.13-SMTfix-Gerber-bottom.png']
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as o:
 for f in items:o.write(f,f.name)
for f in [package,gerber,E/'DTU-V0.13-60x70-SMTfix.epro2']:
 with zipfile.ZipFile(f) as o:assert o.testzip() is None
current=load(M/'current-pcb-delivery-v13.json')
current.update({'revision':'V0.13 SMT碰撞局部修正 2026-10-15','status':'DFM复查中，未完成厂家验收','vias':306,'drilledHoles':322,'nativeProject':str((E/'DTU-V0.13-60x70-SMTfix.epro2').resolve()),'productionGerber':str(gerber.resolve()),'deliveryArchive':str(package.resolve()),'actualCopperManifest':'smt-fixed-actual-routing-v13.json','actualSourceSnapshot':'source-after-smt-fix-v13.json','backupDirectory':str((P/'backups/20261015-before-SMT-collision-fix-154620').resolve()),'files':[{'file':f.name,'bytes':f.stat().st_size} for f in items],'factoryDfmPassed':False,'openDfmItems':['同位号端子碰撞明细待核对','其余PCB/SMT检查分类待取得']})
save(M/'current-pcb-delivery-v13.json',current)
shutil.copy2(M/'smt-fixed-actual-routing-v13.json',M/'final-connected-routing-v13.json');shutil.copy2(M/'smt-fixed-pcb-drc-v13.json',M/'check-pcb-v13.json')
shutil.copy2(M/'smt-fixed-actual-copper-check-v13.json',M/'final-copper-check-v13.json')
save(M/'final-gerber-dfm-check-v13.json',{'silkToMaskMinimumMm':silkgap,'holeToHoleMinimumMm':gap,'allFourCopperLayersPresent':True,'topSmtConnectors':3,'factoryDfmPassed':False,'status':'用户反馈问题复查中'})
save(M/'final-drill-check-v13.json',{n:{'count':len(q),'sizes':dict(collections.Counter(round(v[2],3) for v in q)),'points':q} for n,q in holesBy.items()})
for a,b in [('DTU-V0.13-60x70-SMTfix.epro2','DTU-V0.13-60x70-DFM-review.epro2'),('DTU-V0.13-60x70-SMTfix-Gerber.zip','DTU-V0.13-60x70-SMT-4L-Gerber-DFM.zip'),('DTU-V0.13-60x70-SMT碰撞修正复查包.zip','DTU-V0.13-60x70-验收资料包.zip'),('DTU-V0.13-SMTfix-BOM-99.csv','DTU-V0.13-BOM-99.csv'),('DTU-V0.13-SMTfix-CPL-99-Top.csv','DTU-V0.13-CPL-99-Top.csv')]:shutil.copy2(E/a,E/b)
for layer in ['top','bottom','inner1','inner2']:shutil.copy2(E/f'DTU-V0.13-SMTfix-Gerber-{layer}.png',E/f'DTU-V0.13-Gerber-{layer}.png')
backup=P/'backups/20261015-before-SMT-collision-fix-154620'
if not (backup/'DTU-V0.13-README.md').exists():shutil.copy2(E/'DTU-V0.13-README.md',backup/'DTU-V0.13-README.md')
shutil.copy2(E/'DTU-V0.13-SMTfix-README.md',E/'DTU-V0.13-README.md')
acceptance=D/'V0.13-整体验收记录.md';s=acceptance.read_text(encoding='utf8')
banner='> 当前状态更新：用户 DFM 截图揭示 D6/U7 本体重叠与 U1/Q1 装配余量不足。之前的焊盘检查没有覆盖本体碰撞。两处已局部修正，当前为 SMTfix 复查版（306 过孔、322 总钻孔），完整厂家 DFM 仍未闭环。请以《V0.13-SMT碰撞复核与修正记录.md》和 current-pcb-delivery-v13.json 为准；下文保留 HY20 阶段检查历史。\n\n'
if banner not in s:
 shutil.copy2(acceptance,backup/acceptance.name)
 acceptance.write_text(banner+s,encoding='utf8')
print(json.dumps({'package':str(package),'files':len(items),'DRC':0,'vias':306,'drillHoles':322,'minDrillGapMm':gap,'silkGapMm':silkgap},ensure_ascii=True))
