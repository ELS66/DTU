from pathlib import Path
import json,zipfile,csv,io,hashlib,collections,math,re
P=Path('PCB');root=P/'eda';name='DTU-V0.12-ML307R-DL-60x70';raw=(root/(name+'-Gerber')).read_bytes();(root/(name+'-Gerber.zip')).write_bytes(raw)
src=json.load(open(P/'manifests/pcb-source-release-v12.json',encoding='utf-8'))['result']['source'];records=[]
for line in src.splitlines():
 if '||' not in line:continue
 h,b=line.split('||',1);records.append((json.loads(h),json.loads(b.rstrip('|')) if b.rstrip('|') else {}))
counts=collections.Counter(h['type'] for h,b in records);print('Actual PCB',counts)
assert counts['COMPONENT']==159 and counts['PAD_NET']==549 and counts['FILL']==1794 and counts['VIA']==433
stack=[{'layer':json.loads(h['id'])[1],**b} for h,b in records if h['type']=='LAYER_PHYS'];conductors=[r for r in stack if r['layer'] in [1,15,16,2]];assert len(conductors)==4
assert len(stack)==13
assert [r['layer'] for r in sorted(stack,key=lambda r:r['zIndex']) if r['layer'] in [1,15,16,2]]==[1,15,16,2]
physical_mm=sum(r['thickness']*.0254 for r in stack if r['layer'] not in [3,7,5,6,8,4]);assert abs(physical_mm-1.6)<.001
print('Physical board thickness mm',physical_mm)
(P/'reports/叠层核对-V0.12.json').write_text(json.dumps(stack,ensure_ascii=False,indent=2),encoding='utf-8')
with zipfile.ZipFile(root/(name+'.epro2')) as z:
 assert z.testzip() is None
 meta=json.loads(z.read('project2.json'));assert meta['title']==name
with zipfile.ZipFile(root/(name+'-Gerber.zip')) as z:
 assert z.testzip() is None
 copper={n:{'bytes':len(z.read(n)),'regions':z.read(n).count(b'G36*')} for n in ['Gerber_TopLayer.GTL','Gerber_BottomLayer.GBL','Gerber_InnerLayer1.G1','Gerber_InnerLayer2.G2']};print('Gerber copper',copper)
 assert copper['Gerber_InnerLayer1.G1']['regions']>400 and copper['Gerber_InnerLayer2.G2']['regions']>400
 outline=z.read('Gerber_BoardOutlineLayer.GKO').decode();assert 'X6000000Y7000000' in outline
 drill=z.read('Drill_NPTH_Through.DRL').decode();assert 'T02C3.20000' in drill and all(p in drill for p in ['X4.0Y4.0','X56.0Y4.0','X4.0Y66.0','X56.0Y66.0'])
# The final native export has the same placement as the already audited BOM/assembly table.
pcs=json.load(open(P/'manifests/pcb-pads-release-v12.json',encoding='utf-8'))['result'];old=json.load(open(P/'manifests/pcb-pads-enlarged-v12.json',encoding='utf-8'))['result'];oldby={c['ref']:c for c in old}
assert all(abs(c['x']-oldby[c['ref']]['x'])*.0254<.00001 and abs(c['y']-oldby[c['ref']]['y'])*.0254<.00001 and abs((c['rotation']-oldby[c['ref']]['rotation']+180)%360-180)<0.00001 and c['layer']==oldby[c['ref']]['layer'] for c in pcs)
report={'projectTitle':meta['title'],'counts':counts,'gerberCopper':copper,'boardSizeMm':[60,70],'mountingHoleDiameterMm':3.2,'mountingHoleSpacingMm':[52,62],'fileSha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [root/(name+'.epro2'),root/(name+'-Gerber.zip'),root/'DTU-V0.12-BOM.csv',root/'DTU-V0.12-positions-assembly.csv']},'status':'PASS'}
(P/'reports/交付文件核对-V0.12.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print('DELIVERY PASS')
