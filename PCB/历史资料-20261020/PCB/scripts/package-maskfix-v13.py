from pathlib import Path
import json, zipfile, re, math, csv, io, shutil, hashlib, collections

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
before=source_rows('maskbridge-after-reload-v13.json')
after=source_rows('maskbridge-layout-after-v13.json')
reopened=source_rows('maskbridge-layout-reopen-check-v13.json')
assert after==reopened
changed=[k for k in before.keys()|after.keys() if before.get(k)!=after.get(k)]
assert len(changed)==5 and collections.Counter(k[0] for k in changed)=={'COMPONENT':1,'ATTR':1,'POLY':3}
for k in changed:
    allowed={'COMPONENT':{'x'},'ATTR':{'x'},'POLY':{'path'}}[k[0]]
    assert all(before[k].get(v)==after[k].get(v) for v in before[k].keys()|after[k].keys() if v not in allowed)
    if k[0] in ['COMPONENT','ATTR']:assert abs((after[k]['x']-before[k]['x'])*.0254+.12)<.00001
assert load(M/'mask-layout-pcb-drc-v13.json')['result']==[]
body=load(M/'mask-fixed-body-audit-v13.json')
assert not body['bodyOverlaps'] and not body['uniform5PercentExpansionIntersections']
oldpads={c['ref']:c for c in load(M/'smt-fixed-pcb-pads-v13.json')['result']}
newpads={c['ref']:c for c in load(M/'mask-fixed-pcb-pads-v13.json')['result']}
assert set(oldpads)==set(newpads) and len(newpads)==104
def equivalent(a,b):
    if isinstance(a,(float,int)) and isinstance(b,(float,int)):return abs(a-b)<.0001
    if isinstance(a,dict) and isinstance(b,dict):return a.keys()==b.keys() and all(equivalent(a[k],b[k]) for k in a)
    if isinstance(a,list) and isinstance(b,list):return len(a)==len(b) and all(equivalent(x,y) for x,y in zip(a,b))
    return a==b
assert all(equivalent(newpads[k],oldpads[k]) for k in newpads if k!='R36')
assert all(c['layer']==1 for c in newpads.values())

plan={'routes':[],'vias':[]}
for (kind,id),b in after.items():
    if kind=='VIA':plan['vias'].append({'id':id,'net':b['netName'],'x':b['centerX']*.0254,'y':b['centerY']*.0254,'diameter':b['viaDiameter']*.0254,'hole':b['holeDiameter']*.0254})
    if kind=='POLY' and b['layerId'] in [1,2,15,16] and b['netName']:
        v=[v*.0254 for v in b['path'] if isinstance(v,(int,float))]
        plan['routes'].append({'id':id,'net':b['netName'],'layer':b['layerId'],'widthMm':b['width']*.0254,'pointsMm':list(map(list,zip(v[::2],v[1::2])))})
assert len(plan['vias'])==306 and len(plan['routes'])==509
save(M/'mask-fixed-actual-routing-v13.json',plan)

exec((R/'scripts/render-hy20-gerber-v13.py').read_text(encoding='utf8').split('for label,copper,mask,silk in')[0])
z.close();z=zipfile.ZipFile(E/'DTU-V0.13-60x70-Maskfix-Gerber-raw');cache.clear()
pth=drill('Drill_PTH_Through.DRL');npth=drill('Drill_NPTH_Through.DRL');mounts=[q for q in npth if q[2]>3]
assert len(pth)==316 and len(npth)==6 and len(mounts)==4
oldzip=zipfile.ZipFile(E/'DTU-V0.13-60x70-NPTHfix-Gerber.zip')
layers=['Gerber_TopLayer.GTL','Gerber_BottomLayer.GBL','Gerber_InnerLayer1.G1','Gerber_InnerLayer2.G2']
files=layers+['Gerber_TopSilkscreenLayer.GTO','Gerber_BottomSilkscreenLayer.GBO','Gerber_TopSolderMaskLayer.GTS','Gerber_BottomSolderMaskLayer.GBS','Gerber_TopPasteMaskLayer.GTP','Gerber_BoardOutlineLayer.GKO','Drill_PTH_Through.DRL','Drill_NPTH_Through.DRL']
replacement={};removed=0
for name in layers:
    apertures={};ap=None;out=[];count=0;dark=True
    for line in z.read(name).decode('ascii').splitlines():
        m=re.match(r'%ADD(\d+)C,([.\d]+)\*%',line)
        if m:apertures[int(m[1])]=float(m[2])
        m=re.match(r'G54D(\d+)\*',line)
        if m:ap=int(m[1])
        if line.startswith('%LPC'):dark=False
        if line.startswith('%LPD'):dark=True
        m=re.fullmatch(r'G01X(-?\d+)Y(-?\d+)D03\*',line)
        if m and dark and apertures.get(ap,1)<=.0011:
            xy=(int(m[1])/1e6,int(m[2])/1e6)
            if any(math.dist(xy,q[:2])<.002 for q in mounts):count+=1;continue
        out.append(line)
    assert count==4
    removed+=count;replacement[name]=('\n'.join(out)+'\n').encode('ascii')
# Reopening can produce a 3 nm mask flash from rounded tenting cancellation.
# Remove only the verified existing tented via's non-manufacturable residue.
maskname='Gerber_BottomSolderMaskLayer.GBS';apertures={};ap=None;out=[];mask_residues=[]
for line in z.read(maskname).decode('ascii').splitlines():
    m=re.match(r'%ADD(\d+)C,([.\d]+)\*%',line)
    if m:apertures[int(m[1])]=float(m[2])
    m=re.match(r'G54D(\d+)\*',line)
    if m:ap=int(m[1])
    m=re.fullmatch(r'G01X(-?\d+)Y(-?\d+)D03\*',line)
    if m and apertures.get(ap,1)<.00001:
        xy=(int(m[1])/1e6,int(m[2])/1e6)
        assert math.dist(xy,(17.5,9))<.00001
        assert any(math.dist(xy,(q['x'],q['y']))<.00001 for q in plan['vias'])
        mask_residues.append({'x':xy[0],'y':xy[1],'diameterMm':apertures[ap]});continue
    out.append(line)
assert len(mask_residues)==1
replacement[maskname]=('\n'.join(out)+'\n').encode('ascii')
production=E/'DTU-V0.13-60x70-Maskfix-Gerber.zip'
with zipfile.ZipFile(production,'w',zipfile.ZIP_DEFLATED) as o:
    for name in files:o.writestr(name,replacement.get(name,z.read(name)))
z.close();z=zipfile.ZipFile(production);cache.clear()
from shapely.strtree import STRtree
import shapely
def signature(name):
    return collections.Counter((shapely.to_wkb(shapely.normalize(shapely.set_precision(g,.000001))).hex(),dark) for g,dark in geom(name)[0])
current_features={name:geom(name)[0] for name in files if not name.endswith('.DRL')}
openings=[g for g,d in geom('Gerber_TopSolderMaskLayer.GTS')[0] if d]
tree=STRtree(openings);narrow=[]
for i,g in enumerate(openings):
    for j in tree.query(g.buffer(.1)):
        if j>=i:continue
        gap=g.distance(openings[j])
        if .001<gap<.1:narrow.append([i,int(j),gap])
assert not narrow
local=[g for g in openings if 38.8<g.centroid.x<40.8 and 13.2<g.centroid.y<13.8]
bridge=local[0].distance(local[1]);assert len(local)==2 and .179<bridge<.181
newdrills={n:drill(n) for n in files if n.endswith('.DRL')}
z.close();z=oldzip;cache.clear()
unchanged_layers=[]
for name in current_features:
    if name not in ['Gerber_TopLayer.GTL','Gerber_TopSolderMaskLayer.GTS','Gerber_TopPasteMaskLayer.GTP']:
        previous=geom(name)[0];features=current_features[name]
        assert len(previous)==len(features),name
        index=STRtree([g for g,d in previous]);used=set()
        for g,dark in features:
            candidates=[int(i) for i in index.query(g.centroid.buffer(.00002))
                        if int(i) not in used and previous[i][1]==dark
                        and max(abs(x-y) for x,y in zip(g.bounds,previous[i][0].bounds))<.00001
                        and g.hausdorff_distance(previous[i][0])<.00001]
            assert candidates,(name,g.bounds)
            used.add(candidates[0])
        unchanged_layers.append(name)
for name in newdrills:
    previous=drill(name)
    assert len(previous)==len(newdrills[name])
    remaining=list(previous)
    for x in newdrills[name]:
        i=min(range(len(remaining)),key=lambda i:max(abs(a-b) for a,b in zip(x,remaining[i])))
        assert max(abs(a-b) for a,b in zip(x,remaining[i]))<.00001
        remaining.pop(i)
z.close()

native=list(csv.DictReader(io.StringIO((E/'DTU-V0.13-Maskfix-CPL-native').read_text(encoding='utf-16')),delimiter='\t'))
dnp={'C50','C51','R32','J6','J7'}
cpl=[{'Designator':q['Designator'],'Mid X':q['Mid X'],'Mid Y':q['Mid Y'],'Layer':'Top','Rotation':q['Rotation']} for q in native if q['Designator'] not in dnp]
assert len(cpl)==99 and all(q['Layer']=='T' for q in native)
oldcpl={q['Designator']:q for q in csv.DictReader((E/'DTU-V0.13-NPTHfix-CPL-99-Top.csv').open(encoding='utf-8-sig'))}
assert all(q==oldcpl[q['Designator']] for q in cpl if q['Designator']!='R36')
newr36=next(q for q in cpl if q['Designator']=='R36')
assert abs(float(newr36['Mid X'].removesuffix('mm'))-float(oldcpl['R36']['Mid X'].removesuffix('mm'))+.12)<.001
with (E/'DTU-V0.13-Maskfix-CPL-99-Top.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(cpl[0]));w.writeheader();w.writerows(cpl)
shutil.copy2(E/'DTU-V0.13-NPTHfix-BOM-99.csv',E/'DTU-V0.13-Maskfix-BOM-99.csv')
verification={'pcbDrcIssues':0,'factoryDfmPassed':False,'reopenedSourceVerified':True,'changedSourceRecords':changed,'R36MoveMm':[-.12,0],'targetMaskBridgeMm':bridge,'topMaskSeparateOpeningGapsBelow0_1mm':narrow,'unchangedGerberGeometryLayers':unchanged_layers,'geometryComparisonToleranceMm':.00001,'drillsUnchanged':True,'totalDrills':322,'removedMountPlaceholderFlashes':removed,'components':104,'defaultAssembly':99,'vias':306,'routes':509,'newR36CPL':newr36}
verification['removedNumericalMaskResidues']=mask_residues
save(M/'maskfix-manufacturing-verification-v13.json',verification)
backup=load(M/'maskbridge-backup-v13.json')['directory']
report=D/'V0.13-阻焊桥修正记录.md'
report.write_text(f'''# V0.13 阻焊桥局部修正

2026-10-15。用户 DFM 定位图显示一处约 0.06 mm 的阻焊桥，实际 Gerber 对应 R36/2（TTL_RX_BUF）与 R100/1（VDD_3V3）相邻阻焊开窗。原绿油桥 0.059794 mm，铜间距约 0.161 mm，两侧开窗各外扩 2 mil（0.0508 mm）。这是不同网络焊盘间的真实窄桥，需要处理。

最终采用布局修正：R36 从约 (39.50,14.25) 移到 (39.38,14.25) mm，即左移 0.12 mm；保持封装、方向、铜焊盘尺寸、阻焊外扩和钢网设置。同步移动 3 条连接线的相应端点。原始源码变化仅 1 个 COMPONENT 的 X、随动的隐藏位号 ATTR 的 X 及 3 条 POLY 的端点。其余 103 个封装保持原位。新 CPL 只有 R36 的位置变化，必须与本版 Gerber 配套使用。

导出几何与旧版对照使用 0.00001 mm 容差，以容纳重新打开工程后的微米以下数值取整；并非放宽制造间距。导出器还在原盖油过孔 (17.5,9.0) mm 的背面产生一个直径 0.000003 mm 的数值残点，生产 ZIP 已删除该不可制造的小开窗，保留原盖油意图；没有打开过孔孔口。移除的残点及四角铜占位均写入验证 JSON，原始导出保留供追溯。

曾尝试通过焊盘 API 将两处阻焊外扩设为 0；该接口只影响当前渲染，重新打开工程后没有保留，同时会量化临时焊盘几何，已通过重新打开原工程完整撤回。最终交付采用上述布局修改，不包含该临时开窗尝试。源码已再次关闭/打开验证，布局修正仍保留，阻焊外扩仍为原 2 mil。

验证结果：新 Gerber 该处桥宽 {bridge:.6f} mm（约 0.180 mm）；顶层独立开窗的几何扫描未发现正间隙小于 0.10 mm 的窄桥。该离线几何扫描不等同于 DFM 的平行边算法，不能用其统计数替代厂家复查。原生 PCB DRC=0；库本体无实际重叠、无放大 5% 后重叠。器件 104 个、默认实装 99 个、全在 Top；四层、60×70 mm、306 个过孔、322 个钻孔不变。所有钻孔、板框及非顶层铜几何与前一版一致；原先四角安装孔铜占位清理仍保留（四层共 16 个孔内微小占位点）。

工程：DTU-V0.13-60x70-Maskfix.epro2。生产 Gerber：DTU-V0.13-60x70-Maskfix-Gerber.zip。装配使用 Maskfix-BOM-99.csv 与 Maskfix-CPL-99-Top.csv。完整厂家 DFM、阻焊桥本项的实际复查及首板验证尚未完成；先前其他待确认项继续保留，不宣称整板验收通过。

修改前备份：{backup}。
复核数据：maskfix-manufacturing-verification-v13.json；maskbridge-layout-after-v13.json；maskbridge-layout-reopen-check-v13.json。
工艺资料参考：https://www.jlc.com/portal/q7i37866.html （四层板可设计等大开窗，但本次最终保持原外扩值）。
''',encoding='utf8')
readme=E/'DTU-V0.13-Maskfix-README.md'
readme.write_text('''# V0.13 阻焊桥修正复查包

当前复查版：Maskfix。R36 左移 0.12 mm，原 0.06 mm 阻焊桥增至约 0.18 mm。60×70 mm、四层、单面装配；PCB DRC=0，完整厂家 DFM 尚未完成。

请用 Maskfix-Gerber.zip 重新运行 DFM；装配同时使用 Maskfix-BOM-99.csv 与 Maskfix-CPL-99-Top.csv，勿混用旧 CPL。J6/J7 默认裸孔，不装排针、不焊接。四角无铜孔修正继续保留。

生产 ZIP 已清除四角孔内的 16 个微小占位铜点。原生工程重新导出后仍须按既有安装孔修正规则处理。详情见包内修正记录。

另已清除一个盖油过孔背面直径 0.000003 mm 的导出数值残点；原始导出保留供追溯。
''',encoding='utf8')
package=E/'DTU-V0.13-60x70-阻焊桥修正复查包.zip'
items=[E/'DTU-V0.13-60x70-Maskfix.epro2',production,E/'DTU-V0.13-Maskfix-BOM-99.csv',E/'DTU-V0.13-Maskfix-CPL-99-Top.csv',report,readme,D/'V0.13-下载裸孔装配间距复核.md',D/'V0.13-焊盘距焊盘提示复核记录.md',D/'V0.13-四角无铜安装孔修正记录.md']
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as o:
    for file in items:o.write(file,file.name)
for file in [package,production,items[0]]:
    with zipfile.ZipFile(file) as q:assert q.testzip() is None
current=load(M/'current-pcb-delivery-v13.json')
current.update({'revision':'V0.13 阻焊桥局部修正 2026-10-15','status':'阻焊桥已修正并验证导出几何，待厂家DFM重新检查','nativeProject':str(items[0].resolve()),'productionGerber':str(production.resolve()),'deliveryArchive':str(package.resolve()),'actualSourceSnapshot':'maskbridge-layout-after-v13.json','actualCopperManifest':'mask-fixed-actual-routing-v13.json','actualPadManifest':'mask-fixed-pcb-pads-v13.json','backupDirectory':backup,'maskBridgeReview':str(report.resolve()),'files':[{'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in items]})
current['openDfmItems']=[q for q in current['openDfmItems'] if not q.startswith('阻焊桥')]+['阻焊桥：R36/R100 原0.060mm已增至0.180mm，待本版重新运行DFM确认。']
save(M/'current-pcb-delivery-v13.json',current)
for a,b in [('mask-layout-pcb-drc-v13.json','check-pcb-v13.json'),('mask-fixed-actual-routing-v13.json','final-connected-routing-v13.json')]:shutil.copy2(M/a,M/b)
for a,b in [('DTU-V0.13-60x70-Maskfix.epro2','DTU-V0.13-60x70-DFM-review.epro2'),('DTU-V0.13-60x70-Maskfix-Gerber.zip','DTU-V0.13-60x70-SMT-4L-Gerber-DFM.zip'),('DTU-V0.13-60x70-阻焊桥修正复查包.zip','DTU-V0.13-60x70-验收资料包.zip'),('DTU-V0.13-Maskfix-README.md','DTU-V0.13-README.md')]:shutil.copy2(E/a,E/b)
print(json.dumps(verification,ensure_ascii=True))
