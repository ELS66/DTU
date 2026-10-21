"""Verify and package the two relocated GND vias; never mutates live PCB."""
from pathlib import Path
import json,zipfile,math,re,collections,shutil,hashlib

R=Path('PCB');E=R/'eda';M=R/'manifests';D=R/'docs'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
def source_rows(file):
    out={}
    for line in load(M/file)['result']['source'].splitlines():
        if '||' not in line:continue
        h,b=line.split('||',1);h=json.loads(h)
        if h['type']!='DOCHEAD':out[(h['type'],h.get('id',''))]=json.loads(b.removesuffix('|'))
    return out
before=source_rows('exposure-before-v13.json');after=source_rows('exposure-reopened-source-v13.json')
assert after==source_rows('exposure-after-v13.json')
changed=[k for k in before.keys()|after.keys() if before.get(k)!=after.get(k)]
assert set(changed)=={('VIA','49228cec81f7eb66'),('VIA','6085135c819a0a52'),('POLY','9aeb8ccf2e6c6957'),('POLY','30b7e9410712e557')}
for k in changed:
    allowed={'centerX','centerY'} if k[0]=='VIA' else {'path','width'}
    assert all(before[k].get(v)==after[k].get(v) for v in before[k].keys()|after[k].keys() if v not in allowed)
assert load(M/'exposure-pcb-drc-v13.json')['result']==[]
plan=load(M/'exposure-fixed-actual-routing-v13.json');assert len(plan['vias'])==306 and len(plan['routes'])==509
check=load(M/'exposure-local-verification-v13.json');assert not check['conflicts'] and len(check['U1ThermalPadConnectivity'])==9
assert all(q['groundVias'] for q in check['U1ThermalPadConnectivity'])
exec((R/'scripts/render-hy20-gerber-v13.py').read_text(encoding='utf8').split('for label,copper,mask,silk in')[0])
z.close();z=zipfile.ZipFile(E/'DTU-V0.13-60x70-Exposurefix-Gerber-raw');cache.clear()
pth=drill('Drill_PTH_Through.DRL');npth=drill('Drill_NPTH_Through.DRL');mounts=[q for q in npth if q[2]>3]
assert len(pth)==316 and len(npth)==6 and len(mounts)==4
for x,y in [(40.75,46.9),(18.1,62.25)]:assert any(math.dist((x,y),q[:2])<.00001 and abs(q[2]-.2)<.00001 for q in pth)
for x,y in [(39.9,49.15),(17.8,62.025)]:assert not any(math.dist((x,y),q[:2])<.00001 for q in pth)
layers=['Gerber_TopLayer.GTL','Gerber_BottomLayer.GBL','Gerber_InnerLayer1.G1','Gerber_InnerLayer2.G2']
files=layers+['Gerber_TopSilkscreenLayer.GTO','Gerber_BottomSilkscreenLayer.GBO','Gerber_TopSolderMaskLayer.GTS','Gerber_BottomSolderMaskLayer.GBS','Gerber_TopPasteMaskLayer.GTP','Gerber_BoardOutlineLayer.GKO','Drill_PTH_Through.DRL','Drill_NPTH_Through.DRL']
replacement={};removed_mounts=0;mask_residues=[]
for name in layers+['Gerber_TopSolderMaskLayer.GTS','Gerber_BottomSolderMaskLayer.GBS']:
    aps={};ap=None;out=[];count=0;dark=True
    for line in z.read(name).decode('ascii').splitlines():
        m=re.match(r'%ADD(\d+)C,([.\d]+)\*%',line)
        if m:aps[int(m[1])]=float(m[2])
        m=re.match(r'G54D(\d+)\*',line)
        if m:ap=int(m[1])
        if line.startswith('%LPC'):dark=False
        if line.startswith('%LPD'):dark=True
        m=re.fullmatch(r'G01X(-?\d+)Y(-?\d+)D03\*',line)
        if m and dark:
            pt=(int(m[1])/1e6,int(m[2])/1e6);dia=aps.get(ap,1)
            if name in layers and dia<=.0011 and any(math.dist(pt,q[:2])<.002 for q in mounts):count+=1;continue
            if name not in layers and dia<.00001:
                via=next((q for q in plan['vias'] if math.dist(pt,(q['x'],q['y']))<.00001),None)
                assert via is not None
                raw=after[('VIA',via['id'])];exp=raw['topSolderExpansion' if 'Top' in name else 'bottomSolderExpansion']
                assert abs(raw['viaDiameter']/2+exp)*.0254<.00001
                mask_residues.append({'layer':name,'via':via['id'],'center':pt,'diameterMm':dia});continue
        out.append(line)
    if name in layers:assert count==4;removed_mounts+=count
    replacement[name]=('\n'.join(out)+'\n').encode('ascii')
production=E/'DTU-V0.13-60x70-Exposurefix-Gerber.zip'
with zipfile.ZipFile(production,'w',zipfile.ZIP_DEFLATED) as o:
    for name in files:o.writestr(name,replacement.get(name,z.read(name)))
z.close();z=zipfile.ZipFile(production);cache.clear()
mask=unary_union([g for g,d in geom('Gerber_TopSolderMaskLayer.GTS')[0] if d]);moved=[]
for v in plan['vias']:
    if ('VIA',v['id']) not in changed:continue
    gap=Point(v['x'],v['y']).buffer(v['diameter']/2).distance(mask)
    assert gap>.15
    moved.append({**v,'copperToAllMaskOpeningsMm':gap,'holeToAllMaskOpeningsMm':Point(v['x'],v['y']).distance(mask)-v['hole']/2})
ops=[g for g,d in geom('Gerber_TopSolderMaskLayer.GTS')[0] if d]
rr=[g for g in ops if 38.8<g.centroid.x<40.8 and 13.2<g.centroid.y<13.8]
assert len(rr)==2 and rr[0].distance(rr[1])>.17
drill_gap=min(math.dist(a[:2],b[:2])-(a[2]+b[2])/2 for i,a in enumerate(pth+npth) for b in (pth+npth)[:i]);assert drill_gap>.25
from shapely.strtree import STRtree
preserved=['Gerber_TopSilkscreenLayer.GTO','Gerber_BottomSilkscreenLayer.GBO','Gerber_TopPasteMaskLayer.GTP','Gerber_BoardOutlineLayer.GKO']
current_features={name:geom(name)[0] for name in preserved}
z.close();z=zipfile.ZipFile(E/'DTU-V0.13-60x70-Maskfix-Gerber.zip');cache.clear()
for name in preserved:
    previous=geom(name)[0];features=current_features[name];assert len(previous)==len(features),name
    index=STRtree([g for g,d in previous]);used=set()
    for g,dark in features:
        candidates=[int(i) for i in index.query(g.centroid.buffer(.00002)) if int(i) not in used and previous[i][1]==dark and max(abs(x-y) for x,y in zip(g.bounds,previous[i][0].bounds))<.00001 and g.hausdorff_distance(previous[i][0])<.00001]
        assert candidates,(name,g.bounds)
        used.add(candidates[0])
assert drill('Drill_NPTH_Through.DRL')==npth
z.close()
for suffix in ['BOM-99.csv','CPL-99-Top.csv']:shutil.copy2(E/f'DTU-V0.13-Maskfix-{suffix}',E/f'DTU-V0.13-Exposurefix-{suffix}')
backup=load(M/'exposure-backup-v13.json')['directory']
verification={'changedSourceRecords':changed,'reopenedSourceVerified':True,'componentPlacementsAndPadDefinitionsUnchanged':True,'vias':306,'drills':322,'routes':509,'movedVias':moved,'minimumDrillWallGapMm':drill_gap,'modifiedCopperMinimumClearanceMm':check['modifiedCopperMinimumClearanceMm'],'U1AllNineGroundPadsReachVias':True,'R36R100MaskBridgeMm':rr[0].distance(rr[1]),'removedMountPlaceholders':removed_mounts,'removedNumericalMaskResidues':mask_residues,'PCB_DRC':0,'factoryDfmPassed':False}
save(M/'exposurefix-manufacturing-verification-v13.json',verification)
doc=D/'V0.13-开窗露线四项修正记录.md'
doc.write_text(f'''# V0.13 开窗露线四项布局修正

2026-10-15。本版 Exposurefix 接续 Maskfix，已实际修改两处 GND 过孔及两条接地线，取代此前仅作工艺待确认的处置。

ESP32 U1 底部原 (39.90,49.15) mm 处的过孔，移至散热地焊盘阵列下侧 (40.75,46.90) mm。原 0.254 mm 斜向引线改为 0.50 mm 宽的接地线，贯通中间两块同号 29 的 GND 焊盘并引至新位置。九块散热地焊盘铜尺寸、钢网、开窗及全部器件位置保持不变。已按九个不同焊盘唯一 ID 逐一核对：全部仍可经顶层 GND 铜到达接地过孔，中间两块地焊盘可到达两个接地过孔。此项仅证明连接结构，未宣称热仿真或射频实测通过。

下载口附近原 (17.80,62.025) mm 处的 GND 过孔，移至 (18.10,62.25) mm，同步调整原有接地线端点。该孔原来与 D10/2 开窗间距约 0.0039 mm，现在远离 D10 及周边其他开窗。

新导出 Gerber 中，以上两个过孔外圈铜至全部顶层开窗的最小间距分别约 0.470 mm、0.274 mm，超过 DFM 的 0.15 mm 良好阈值。对应孔口距开窗更大，仍为盖油孔。原四项危险对应两个过孔与四个开窗，原位置的孔及圆盘已经移走；源记录只变化 2 个 VIA 的坐标、2 个 POLY 的路径（其中一条加宽）。

原生工程已保存、关闭、重开并重新检查：PCB DRC=0。修改铜图形至异网铜最小约 {check['modifiedCopperMinimumClearanceMm']:.3f} mm，无新增非铺铜铜间距冲突。全部钻孔最小孔壁距离约 {drill_gap:.3f} mm。306 个过孔、322 个钻孔、509 条线记录保持不变。未缩小孔径/铜环，仍为 Ø0.45/Ø0.20 mm；104 个封装、99 件实装、四层、单面装配、60×70 mm 保持不变。器件位置及 BOM/CPL 完全不变，仍复制为本版名称以便配套使用。上一版 R36/R100 的约 0.180 mm 阻焊桥修正继续保留。

生产 ZIP 保留既有四角 NPTH 处理：移除四层共 16 个孔内最小铜占位点。若导出器在盖油过孔处产生数纳米的阻焊开窗残点，仅在核对它是该盖油孔数值抵消残差后清理，全部逐项写入验证 JSON；原始导出保留。正式生产 Gerber 使用 Exposurefix-Gerber.zip，不能直接使用 raw。

原有七项焊盘间距告警中，D10/2 与 U1 三块散热地焊盘的四个对应位置已随本次移动修正；D9、C33、LTE_BOOT 的三项是其他位置，仍保留既有工艺复核状态。整板厂家 DFM、其余加工项和首板验证尚未闭环。新间距是导出几何验证结果，尚不能替代用户用新资料重跑嘉立创 DFM 的实际结果；没有修改或屏蔽 DFM 阈值。

修改前备份：{backup}。
依据：exposure-before-v13.json；exposure-reopened-source-v13.json；exposure-fixed-actual-routing-v13.json；exposure-local-verification-v13.json；exposurefix-manufacturing-verification-v13.json。
''',encoding='utf8')
readme=E/'DTU-V0.13-Exposurefix-README.md'
readme.write_text('''# V0.13 开窗露线修正复查包

当前版 Exposurefix：两个 GND 过孔移位，四项对应位置至开窗的最小间距增至约 0.274/0.470 mm。PCB DRC=0；整板厂家 DFM 尚未通过验收。

导入 Exposurefix-Gerber.zip 重跑 DFM。装配配套使用 Exposurefix-BOM-99.csv 与 Exposurefix-CPL-99-Top.csv（器件坐标与 Maskfix 相同）。原生工程及修正记录均在包内。

60×70 mm、四层、单面贴装、104 个封装/99 件实装，306 个过孔、322 个钻孔。原有 R36 阻焊桥及四角无铜安装孔修正保留。J6/J7 默认裸孔，不装不焊。生产 ZIP 已清除已确认的孔内铜占位及极小阻焊数值残点；原生自行重新导出后需要同样核对。
''',encoding='utf8')
items=[E/'DTU-V0.13-60x70-Exposurefix.epro2',production,E/'DTU-V0.13-Exposurefix-BOM-99.csv',E/'DTU-V0.13-Exposurefix-CPL-99-Top.csv',doc,readme]
package=E/'DTU-V0.13-60x70-开窗露线修正复查包.zip'
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as o:
    for file in items:o.write(file,file.name)
for file in [package,production,items[0]]:
    with zipfile.ZipFile(file) as q:assert q.testzip() is None
current=load(M/'current-pcb-delivery-v13.json')
current.update({'revision':'V0.13 开窗露线局部修正 2026-10-15','status':'两处GND过孔移位完成，四项开窗露线待新Gerber重跑DFM','nativeProject':str(items[0].resolve()),'productionGerber':str(production.resolve()),'deliveryArchive':str(package.resolve()),'actualSourceSnapshot':'exposure-reopened-source-v13.json','actualCopperManifest':'exposure-fixed-actual-routing-v13.json','backupDirectory':backup,'openingClearanceReview':str(doc.resolve()),'files':[{'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in items]})
current['openDfmItems']=[q for q in current['openDfmItems'] if not q.startswith(('开窗露线4项','焊盘距焊盘7项'))]+['开窗露线4项对应两处GND过孔已移位，实际开窗间距约0.274/0.470mm，待新资料重跑DFM。','原7项焊盘间距中D10及ESP32四项位置已移位修正；余下D9/C33/LTE_BOOT三项维持既有工艺待确认状态。']
save(M/'current-pcb-delivery-v13.json',current)
for a,b in [('exposure-pcb-drc-v13.json','check-pcb-v13.json'),('exposure-fixed-actual-routing-v13.json','final-connected-routing-v13.json')]:shutil.copy2(M/a,M/b)
for a,b in [('DTU-V0.13-60x70-Exposurefix.epro2','DTU-V0.13-60x70-DFM-review.epro2'),('DTU-V0.13-60x70-Exposurefix-Gerber.zip','DTU-V0.13-60x70-SMT-4L-Gerber-DFM.zip'),('DTU-V0.13-60x70-开窗露线修正复查包.zip','DTU-V0.13-60x70-验收资料包.zip'),('DTU-V0.13-Exposurefix-README.md','DTU-V0.13-README.md')]:shutil.copy2(E/a,E/b)
prior=M/'dfm-four-opening-clearance-review-v13.json';d=load(prior);d['supersededBy']='exposurefix-manufacturing-verification-v13.json';d['latestDisposition']='两个过孔已移位，此记录仅保留修改前几何复核。';save(prior,d)
print(json.dumps(verification,ensure_ascii=True))
