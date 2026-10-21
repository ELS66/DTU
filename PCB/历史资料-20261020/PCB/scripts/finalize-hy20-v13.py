"""Verify actual exported HY2.0 fabrication files and prepare assembly tables."""
from pathlib import Path
import json, csv, io, math, collections, zipfile
P=Path('PCB'); E=P/'eda'; M=P/'manifests'
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d): p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
assert load(M/'hy20-final-pcb-drc-v13.json')['result']==[]
erc=load(M/'hy20-sch-drc-v13.json')['result']
assert len(erc)==18 and all(r['type']=='warn' for r in erc)
exec((P/'scripts/render-hy20-gerber-v13.py').read_text(encoding='utf-8-sig').split('for label,copper,mask,silk in')[0])
drillsets={n:drill('Drill_'+n+'_Through.DRL') for n in ['PTH','NPTH']}
allholes=drillsets['PTH']+drillsets['NPTH']
assert len(allholes)==320 and len(drillsets['PTH'])==314 and len(drillsets['NPTH'])==6
mind=100;pair=None
for i,a in enumerate(allholes):
 for b in allholes[:i]:
  d=math.dist(a[:2],b[:2])-(a[2]+b[2])/2
  if d<mind: mind=d;pair=[a,b]
mask=unary_union([g for g,d in geom('Gerber_TopSolderMaskLayer.GTS')[0] if d])
silk=unary_union([g for g,d in geom('Gerber_TopSilkscreenLayer.GTO')[0] if d])
silkclear=mask.distance(silk)
assert mind>.25 and silkclear>.15
files=['Gerber_TopLayer.GTL','Gerber_BottomLayer.GBL','Gerber_InnerLayer1.G1','Gerber_InnerLayer2.G2','Gerber_TopSilkscreenLayer.GTO','Gerber_BottomSilkscreenLayer.GBO','Gerber_TopSolderMaskLayer.GTS','Gerber_BottomSolderMaskLayer.GBS','Gerber_TopPasteMaskLayer.GTP','Gerber_BoardOutlineLayer.GKO','Drill_PTH_Through.DRL','Drill_NPTH_Through.DRL']
for n in files: assert n in z.namelist()
assert all(geom(n)[0] for n in files[:4])
assert 'Gerber_BottomPasteMaskLayer.GBP' not in z.namelist()
pads=load(M/'hy20-final-pcb-pads-v13.json')['result']; assert len(pads)==104
assert all(c['layer']==1 for c in pads)
before=load(P/'backups/20261015-before-HY20-connector/pads-after-routing-opt-v13.json')['result']
old={c['ref']:c for c in before}; sch=load(E/'DTU-V0.13-HY20-schematic-netlist')['components']
assert len(sch)==104
for c in pads:
 s=sch[c['uid']]; assert s['props']['Designator']==c['ref']
 for p in c['pads']:
  assert p['net']==s['pinInfoMap'].get(p['number'],{}).get('net',''),(c['ref'],p['number'])
 if c['ref'] not in ['J1','J2','J3']:
  for k in ['x','y','rotation','layer','footprint','pads']: assert c[k]==old[c['ref']][k],(c['ref'],k)
measure=[]
for c in pads:
 if c['ref'] not in ['J1','J2','J3']: continue
 assert c['rotation']==0 and len(c['pads'])==6
 pp={p['number']:p for p in c['pads']}
 for n,p in pp.items():
  assert p['layer']==1
  w,h=[v*.0254 for v in p['shape'][1:3]]
  assert abs(w-(1.5 if int(n)<5 else 1.6))<.003 and abs(h-3)<.003
  x,y=p['x']*.0254,p['y']*.0254
  # Verify standalone flashes in each actual fabrication layer, not just SDK data.
  for layer,expansion in [('Gerber_TopLayer.GTL',0),('Gerber_TopSolderMaskLayer.GTS',.1),('Gerber_TopPasteMaskLayer.GTP',0)]:
   matches=[]
   for g,dark in geom(layer)[0]:
    if not dark or g.is_empty: continue
    a,b,cc,dd=g.bounds
    if abs((a+cc)/2-x)<.004 and abs((b+dd)/2-y)<.004 and abs(cc-a-(w+expansion))<.006 and abs(dd-b-(h+expansion))<.006: matches.append(g)
   assert matches,(c['ref'],n,layer)
  assert all(not Point(x,y).buffer(.65).contains(Point(*v[:2])) for v in allholes),(c['ref'],n,'drill near SMT pad center')
 rowgap=(pp['1']['y']-pp['5']['y'])*.0254; fixedspan=(pp['6']['x']-pp['5']['x'])*.0254
 assert abs(rowgap-3)<.004 and abs(fixedspan-10.7)<.004
 measure.append({'ref':c['ref'],'centerMm':[c['x']*.0254,c['y']*.0254],'rotation':c['rotation'],'signalPitchMm':(pp['2']['x']-pp['1']['x'])*.0254,'signalToFixedRowMm':rowgap,'fixedPadSpanMm':fixedspan,'topSmtPads':6})
target=E/'DTU-V0.13-60x70-HY20-Gerber.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as out:
 for n in files: out.writestr(n,z.read(n))
result={'totalDrilledHoles':320,'PTH':314,'NPTH':6,'drillDiameters':dict(collections.Counter(round(h[2],3) for h in allholes)),'minimumDrillWallGapMm':mind,'closestDrills':pair,'topSilkMaskClearanceMm':silkclear,'manufacturingFileCount':12,'removedDuplicateViaDrill':True,'copperLayers':4,'assemblySide':'Top only','terminalMeasurements':measure,'verifiedGerberPadLayers':['GTL','GTS','GTP'],'factoryDFM':'Pending'}
save(M/'hy20-manufacturing-check-v13.json',result)
save(M/'final-drill-check-v13.json',{n:{'count':len(q),'sizes':dict(collections.Counter(round(v[2],3) for v in q)),'points':q} for n,q in drillsets.items()})
rows=[]
for l in load(M/'hy20-final-pcb-source-v13.json')['result']['source'].splitlines():
 if '||' in l:
  h,b=l.split('||',1);rows.append((json.loads(h),json.loads(b.removesuffix('|'))))
plan={'routes':[],'vias':[]}
for h,b in rows:
 if h['type']=='VIA':plan['vias'].append({'id':h['id'],'net':b['netName'],'x':b['centerX']*.0254,'y':b['centerY']*.0254,'diameter':b['viaDiameter']*.0254,'hole':b['holeDiameter']*.0254})
 if h['type']=='POLY' and b['layerId'] in [1,2,15,16] and b['netName']:
  assert all(not isinstance(v,str) or v=='L' for v in b['path'])
  vals=[v*.0254 for v in b['path'] if isinstance(v,(int,float))]
  plan['routes'].append({'id':h['id'],'net':b['netName'],'layer':b['layerId'],'widthMm':b['width']*.0254,'pointsMm':list(map(list,zip(vals[::2],vals[1::2])))})
assert len(plan['vias'])==304
save(M/'hy20-final-routing-source-v13.json',plan)
save(M/'hy20-final-source-verification-v13.json',{'components':104,'unchangedOtherComponents':101,'allPinNetsMatchSchematic':True,'topAssembly':True,'vias':304,'routes':len(plan['routes']),'pcbDrcIssues':0,'schematicWarnings':len(erc)})
def writecsv(path,keys,rows):
 with path.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
for src,dest,review in [('DTU-V0.13-BOM-99.csv','DTU-V0.13-HY20-BOM-99.csv',False),('DTU-V0.13-BOM-review.csv','DTU-V0.13-HY20-BOM-review.csv',True)]:
 rr=list(csv.DictReader((E/src).open(encoding='utf-8-sig')));keys=list(rr[0])
 for r in rr:
  if r[keys[0]] in ['J1','J2','J3']:
   if review:
    r[keys[1]]=r[keys[2]]='ZX-HY2.0-4PLT';r[keys[3]]='C7429562';r[keys[4]]='CONN-SMD_4P-P2.00_HY2.0-4P'
   else: r.update({'Comment':'ZX-HY2.0-4PLT','Footprint':'CONN-SMD_4P-P2.00_HY2.0-4P','LCSC Part #':'C7429562'})
 writecsv(E/dest,keys,rr)
dnp={'C50','C51','R32','J6','J7'}
native=list(csv.DictReader(io.StringIO((E/'DTU-V0.13-HY20-CPL-native').read_text(encoding='utf-16')),delimiter='\t'))
assert len(native)==104
cpl=[]
for r in native:
 if r['Designator'] in dnp: continue
 assert r['Layer']=='T'
 cpl.append({'Designator':r['Designator'],'Mid X':r['Mid X'],'Mid Y':r['Mid Y'],'Layer':'Top','Rotation':r['Rotation']})
assert len(cpl)==99
for r in cpl:
 c=next(c for c in pads if c['ref']==r['Designator'])
 expectedY=c['y']*.0254
 if c['ref'] in ['J1','J2','J3']:
  pp={p['number']:p for p in c['pads']}
  expectedY=(pp['1']['y']+pp['5']['y'])/2*.0254
 assert abs(float(r['Mid X'].removesuffix('mm'))-c['x']*.0254)<.002 and abs(float(r['Mid Y'].removesuffix('mm'))-expectedY)<.002
 assert abs((float(r['Rotation'])-c['rotation']+180)%360-180)<.001
assert {r['Designator'] for r in cpl}=={r['Designator'] for r in csv.DictReader((E/'DTU-V0.13-HY20-BOM-99.csv').open(encoding='utf-8-sig'))}
writecsv(E/'DTU-V0.13-HY20-CPL-99-Top.csv',list(cpl[0]),cpl)
print(json.dumps({'manufacturing':result,'assemblyRows':len(cpl),'routes':len(plan['routes'])},ensure_ascii=True,indent=2))
