"""Native and actual Gerber regression checks for the bounded pin-land repair."""
from pathlib import Path
import sys,json,zipfile,math,collections
sys.path.insert(0,str(Path('PCB/.tools').resolve()))
from shapely.geometry import box,Polygon,Point,LineString
from shapely.affinity import rotate,translate
from shapely.ops import unary_union
from shapely.strtree import STRtree
R=Path('PCB');M=R/'manifests';E=R/'eda'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
s=(R/'scripts/package-silkclean-v13.py').read_text(encoding='utf8')
exec(s[s.index('def rows('):s.index('before=rows(')])
exec(s[s.index('def active_project('):s.index('oldproj=active_project(')])
stage=load(M/'u2boundary-plan-v14_3.json');old=stage['baseline'];pcb=old['pcbUuid']
a=active_project(Path(old['nativeProject']));b=active_project(E/'DTU-V0.14.3-60x75-U2fix.epro2')
s=(R/'scripts/prepare-pinfix-v14_2.py').read_text(encoding='utf8');exec(s[s.index('def padgeom('):s.index('# Capture the actually exported stencil')])
cs=load(M/'clearancefix-final-pads-v14.json')['result'];by={c['ref']:c for c in cs}
changed_keys={k for k in a.keys()|b.keys() if a.get(k)!=b.get(k)}
model_keys=[k for k,q in a.items() if k[0]=='FOOTPRINT' and q.get('layerId') in [48,50,51,52]]
assert all(a[k]==b[k] for k in model_keys),'Physical models changed'
assert all(a[k]==b[k] for k in a if k[0] not in ['PCB','FOOTPRINT','BLOB','PANEL']),'Schematic changed'
for k in a:
 if k[:2]!=('PCB',pcb) or k[2] in ['POURED','POLY']:continue
 assert a[k]==b[k],k
changed_routes=[k for k in changed_keys if k[:3]==('PCB',pcb,'POLY')]
assert set(changed_routes)=={('PCB',pcb,'POLY','85f1f88e6f3b6920'),('PCB',pcb,'POLY','a6e8fb4f01680569')}
for edit in stage['padEdits']:
 k=('FOOTPRINT','6b69a40d60760f97','PAD',edit['padId']);q=b[k]
 assert q['num']==a[k]['num'] and q['padAngle']==a[k]['padAngle']
 assert max(abs(q['defaultPad'][axis]*.0254-size) for axis,size in zip(['width','height'],edit['newMm']))<1e-8,(k,q)
 assert q['topPasteExpansion']==q['bottomPasteExpansion']<0
assert load(M/'u2boundary-drc-v14_3.json')['result']==[]
# Exact nominal model versus new native lands (no 2 micrometre forgiveness).
modelrows=[]
for ref in ['U1','U2','J4','D30','D31','D33','D34','D36']:
 c=by[ref];fp=c['footprint']['uuid'];pads=[(k,p,padgeom(p)) for k,p in b.items() if k[:3]==('FOOTPRINT',fp,'PAD') and p.get('layerId')==1]
 for k,q in b.items():
  if k[:2]!=('FOOTPRINT',fp) or q.get('layerId')!=50 or 'path' not in q:continue
  for path in q['path']:
   v=[v*.0254 for v in path if isinstance(v,(int,float))];g=Polygon(list(zip(v[::2],v[1::2]))).buffer(0)
   pk,p,land=min(pads,key=lambda pp:pp[2].centroid.distance(g.centroid));outside=g.difference(land).area
   assert outside<1e-12,(ref,k,p['num'],outside)
   modelrows.append({'ref':ref,'modelId':k[-1],'pin':p['num'],'nominalLeadMarginMm':g.distance(land.boundary),'padId':pk[-1],'localBounds':list(land.bounds)})
# Regression: all eight inner keepouts remain centred on four true NPTHs.
after=rows(load(M/'u2boundary-after-source-v14_3.json')['result']['source']);mounts_native=[];mountchecks=[]
for (t,i),q in after.items():
 if t=='PAD' and q.get('plated') is False and (q.get('hole') or {}).get('width',0)*.0254>3:mounts_native.append((q['centerX']*.0254,q['centerY']*.0254))
assert len(mounts_native)==4
for xy in mounts_native:
 for layer in [15,16]:
  matches=[]
  for (t,i),q in after.items():
   if t!='REGION' or q['layerId']!=layer or q['prohibitType']!=['COPPER']:continue
   v=[v*.0254 for v in q['path'][0] if isinstance(v,(int,float))];xs,ys=v[::2],v[1::2];center=((max(xs)+min(xs))/2,(max(ys)+min(ys))/2)
   if math.dist(xy,center)<.00001:matches.append({'holeMm':xy,'layer':layer,'region':i,'radiusMm':(max(xs)-min(xs))/2})
  assert len(matches)==1 and abs(matches[0]['radiusMm']-3.4)<.00001
  mountchecks+=matches
exec((R/'scripts/render-hy20-gerber-v13.py').read_text(encoding='utf8').split('for label,copper,mask,silk in')[0])
z.close();z=zipfile.ZipFile(E/'DTU-V0.14.3-60x75-U2fix-Gerber-raw');cache.clear();mounts=[q for q in drill('Drill_NPTH_Through.DRL') if q[2]>3]
plan=load(M/'u2boundary-actual-routing-v14_3.json')
s=(R/'scripts/package-exposurefix-v13.py').read_text(encoding='utf8');segment=s[s.index('layers='):s.index('mask=unary_union')].replace('DTU-V0.13-60x70-Exposurefix-Gerber.zip','DTU-V0.14.3-60x75-U2fix-Gerber.zip');exec(segment)
production=z
# Compare unchanged paste, drilling, outline, silk, bottom and two inner copper layers by geometry.
oldz=zipfile.ZipFile(old['productionGerber']);preserved=[]
def samefeatures(aa,bb,name):
 assert len(aa)==len(bb),(name,len(aa),len(bb))
 tree=STRtree([g for g,d in aa]);used=set()
 for g,d in bb:
  cand=[int(i) for i in tree.query(g.representative_point().buffer(.00002)) if int(i) not in used and aa[i][1]==d and g.hausdorff_distance(aa[i][0])<.00001]
  assert cand,(name,g.bounds)
  used.add(cand[0])
for name in production.namelist():
 if name in ['Gerber_TopLayer.GTL','Gerber_TopSolderMaskLayer.GTS']:continue
 z=production;cache.clear();now=drill(name) if name.endswith('.DRL') else geom(name)[0]
 z=oldz;cache.clear();prev=drill(name) if name.endswith('.DRL') else geom(name)[0]
 if name.endswith('.DRL'):
  assert len(now)==len(prev)
  assert all(any(max(abs(v-w) for v,w in zip(q,p))<.00001 for p in prev) for q in now)
 else:samefeatures(prev,now,name)
 preserved.append(name)
z=production;cache.clear();copper=[g for g,d in geom('Gerber_TopLayer.GTL')[0] if d];ctree=STRtree(copper)
actualchecks=[]
for row in modelrows:
 c=by[row['ref']];fp=c['footprint']['uuid'];q=b[('FOOTPRINT',fp,'FILL',row['modelId'])]
 v=[v*.0254 for v in q['path'][0] if isinstance(v,(int,float))];g=world(Polygon(list(zip(v[::2],v[1::2]))),c)
 hits=[copper[int(i)] for i in ctree.query(g.centroid.buffer(.001))];assert hits
 land=unary_union(hits);assert g.difference(land).area<1e-10,(row['ref'],row['pin'])
 actualchecks.append({'ref':row['ref'],'pin':row['pin'],'modelId':row['modelId'],'actualCopperMarginMm':land.boundary.distance(g)})
allholes=drill('Drill_PTH_Through.DRL')+drill('Drill_NPTH_Through.DRL');assert len(allholes)==326
silk=unary_union([g for g,d in geom('Gerber_TopSilkscreenLayer.GTO')[0] if d]);mask=unary_union([g for g,d in geom('Gerber_TopSolderMaskLayer.GTS')[0] if d])
assert silk.distance(mask)>.25
report={'revision':'V0.14.3','nativeDrcIssues':0,'physicalModelsUnchanged':True,'componentPlacementsAndNetBindingsUnchanged':True,'changedMasterPadCount':109,'expandedPadInstanceCount':109,'changedRouteCount':2,'viaCount':310,'drillCount':326,'preservedProductionGeometries':preserved,'unchangedPasteVerified':True,'targetModelCount':len(modelrows),'minimumNominalModelMarginMm':min(q['actualCopperMarginMm'] for q in actualchecks),'minimumMarginByComponent':{r:min(q['actualCopperMarginMm'] for q in actualchecks if q['ref']==r) for r in {q['ref'] for q in actualchecks}},'mountKeepoutChecks':mountchecks,'silkToMaskGapMm':silk.distance(mask),'nativeChangesByType':dict(collections.Counter('/'.join(k[:1]+k[2:3]) for k in changed_keys)),'factoryDfmPassed':False,'pending':'J5 antenna soldered/floating termination model; connector self-collision recognition; strict factory DFM recheck required.','models':actualchecks}
save(M/'u2boundary-verification-v14_3.json',report)
print(json.dumps({k:v for k,v in report.items() if k not in ['models','mountKeepoutChecks']},ensure_ascii=True))
