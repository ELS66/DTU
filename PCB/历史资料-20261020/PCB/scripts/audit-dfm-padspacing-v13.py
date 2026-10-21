from pathlib import Path
import json
root=Path('PCB')
exec((root/'scripts/router-v13.py').read_text(encoding='utf8').replace('read-pcb-pads-v13.json','smt-fixed-pcb-pads-v13.json'))
from shapely.strtree import STRtree
plan=json.loads((root/'manifests/smt-fixed-actual-routing-v13.json').read_text());obs=[]
for pad in pads:obs.append({'kind':'pad','id':pad['id'],'ref':pad['ref'],'number':pad['number'],'net':pad['net'],'layer':pad['layer'],'geom':pad['geom'],'shape':pad['shape'],'x':pad['x'],'y':pad['y']})
for v in plan['vias']:obs.append({'kind':'via','id':v['id'],'ref':v['id'],'net':v['net'],'layer':12,'geom':Point(v['x'],v['y']).buffer(v['diameter']/2),'x':v['x'],'y':v['y'],'diameter':v['diameter'],'hole':v['hole']})
tr=STRtree([o['geom'] for o in obs]);pairs=[]
for i,a in enumerate(obs):
 for j in tr.query(a['geom'].buffer(.15)):
  if j>=i:continue
  b=obs[j]
  if a['layer']!=b['layer'] and 12 not in [a['layer'],b['layer']]:continue
  gap=a['geom'].distance(b['geom'])
  if .0005<gap<.15:pairs.append({'a':{k:v for k,v in a.items() if k!='geom'},'b':{k:v for k,v in b.items() if k!='geom'},'gapMm':gap,'sameNet':bool(a['net'] and a['net']==b['net'])})
pairs.sort(key=lambda r:r['gapMm'])
exec((root/'scripts/render-hy20-gerber-v13.py').read_text(encoding='utf8').split('for label,copper,mask,silk in')[0])
z.close();z=zipfile.ZipFile(root/'eda/DTU-V0.13-60x70-NPTHfix-Gerber.zip');cache.clear()
g=Polygon();block=[];mode=True
for f,dark in geom('Gerber_TopLayer.GTL')[0]:
 if dark!=mode:
  b=unary_union(block);g=g.union(b) if mode else g.difference(b);block=[];mode=dark
 block.append(f)
b=unary_union(block);g=g.union(b) if mode else g.difference(b)
polys=list(g.geoms) if hasattr(g,'geoms') else [g];tree=STRtree(polys)
def island(o):
 pt=Point(o['x'],o['y']);return set(int(i) for i in tree.query(pt.buffer(.005)) if polys[i].distance(pt)<.005)
distinct=[]
for pair in pairs:
 if pair['a']['layer'] not in [1,12] or pair['b']['layer'] not in [1,12]:continue
 a,b=island(pair['a']),island(pair['b'])
 if not a&b:distinct.append({**pair,'aCopperIslands':list(a),'bCopperIslands':list(b)})
mask=unary_union([g for g,d in geom('Gerber_TopSolderMaskLayer.GTS')[0] if d]);uv={}
for pair in pairs:
 if pair['gapMm']>=.1:continue
 for o in [pair['a'],pair['b']]:
  if o['kind']=='via':uv[o['id']]=o
viaMask=[]
for v in uv.values():
 pt=Point(v['x'],v['y']);viaMask.append({'via':v['id'],'net':v['net'],'x':v['x'],'y':v['y'],'holeExposed':mask.intersects(pt.buffer(v['hole']/2)),'holeToMaskOpeningGapMm':mask.distance(pt)-v['hole']/2})
for file,data in [('dfm-pad-spacing-pairs-v13.json',pairs),('dfm-isolated-pad-spacing-v13.json',distinct)]:
 (root/'manifests'/file).write_text(json.dumps(data,indent=2),encoding='utf8')
result={'allNearPairsSameNet':all(p['sameNet'] for p in pairs if p['gapMm']<.1),'nearPairs':sum(p['gapMm']<.1 for p in pairs),'distinctCopperIslandsNearPairs':[p for p in distinct if p['gapMm']<.1],'distinctCopperIslandsWarningPairs':[p for p in distinct if p['gapMm']>=.1],'holesCovered':all(not q['holeExposed'] for q in viaMask),'vias':viaMask,'usesUniquePadIds':True}
(root/'manifests/dfm-pad-spacing-final-assessment-v13.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps({'nearPairs':result['nearPairs'],'sameNet':result['allNearPairsSameNet'],'coveredHoles':result['holesCovered'],'distinctDanger':len(result['distinctCopperIslandsNearPairs']),'distinctWarning':len(result['distinctCopperIslandsWarningPairs']),'dangerRefs':[(p['a']['ref'],p['b']['ref'],p['b'].get('number'),p['gapMm']) for p in result['distinctCopperIslandsNearPairs']]},indent=2))
