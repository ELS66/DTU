from pathlib import Path
import json,zipfile,math,copy
R=Path('PCB');M=R/'manifests';E=R/'eda'
exec((R/'scripts/router-v13.py').read_text(encoding='utf8').replace('read-pcb-pads-v13.json','clearancefix-final-pads-v14.json'))
from shapely.strtree import STRtree
plan=json.loads((M/'clearancefix-actual-routing-v14.json').read_text(encoding='utf8'));vid='1c8a7c730c47500a';v=next(q for q in plan['vias'] if q['id']==vid);old=(v['x'],v['y']);attached=[r for r in plan['routes'] if r['net']==v['net'] and any(math.dist(pt,old)<.005 for pt in r['pointsMm'])]
for r in plan['routes']:
 if r in attached:continue
 tracks.append({'net':r['net'],'layer':r['layer'],'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2),'points':r['pointsMm']})
vias.extend(plan['vias']);layer_obstacles={lay:obstacles(v['net'],lay) for lay in [1,2,15,16]};obs=unary_union(list(layer_obstacles.values()))
router_holes=holes
exec((R/'scripts/render-hy20-gerber-v13.py').read_text(encoding='utf8').split('for label,copper,mask,silk in')[0]);z.close();z=zipfile.ZipFile(E/'DTU-V0.14-60x75-Clearancefix-Gerber.zip');cache.clear();mask=unary_union([g for g,d in geom('Gerber_TopSolderMaskLayer.GTS')[0] if d]);opts=[];holes=router_holes
for ix in range(-10,11):
 for iy in range(-10,11):
  x=round(old[0]+ix*.025,3);y=round(old[1]+iy*.025,3);pt=Point(x,y)
  if pt.buffer(v['diameter']/2).distance(mask)<.22 or pt.distance(obs)<v['diameter']/2+.154:continue
  if any(math.dist((x,y),(q['x'],q['y']))-(v['hole']+q['hole'])/2<.31 for q in plan['vias'] if q['id']!=vid):continue
  candidates=[];safe=True
  for r in attached:
   q=copy.deepcopy(r)
   for p in q['pointsMm']:
    if math.dist(p,old)<.005:p[:]=[x,y]
   if LineString(q['pointsMm']).distance(layer_obstacles[q['layer']])<q['widthMm']/2+.153:safe=False;break
   candidates.append(q)
  if safe:opts.append((math.dist((x,y),old),x,y,candidates))
assert opts,'No safe mask-clearance candidate';_,x,y,rs=min(opts,key=lambda q:q[0]);ids=json.loads((M/'clearancefix-native-id-map-v14.json').read_text(encoding='utf8'));expected=json.loads((M/'clearancefix-rerouted-plan-v14.json').read_text(encoding='utf8'));inv={v:k for k,v in ids['routes'].items()};iv={v:k for k,v in ids['vias'].items()};ev=next(q for q in expected['vias'] if q['id']==iv[vid]);ev['x'],ev['y']=x,y
for r in rs:next(q for q in expected['routes'] if q['id']==inv[r['id']])['pointsMm']=r['pointsMm']
guard=(R/'scripts/read-clearancefix-source-v14.js').read_text(encoding='utf8').split('return {source:')[0]
args={'via':vid,'old':list(old),'target':[x,y],'diameter':v['diameter'],'hole':v['hole'],'routes':rs}
js=guard+'const a='+json.dumps(args)+";const v=await eda.pcb_PrimitiveVia.get(a.via);if(!v||Math.abs(v.getState_X()*.0254-a.old[0])>.003||Math.abs(v.getState_Y()*.0254-a.old[1])>.003)throw Error('Via baseline changed');if(!await eda.pcb_PrimitiveVia.modify(a.via,{x:a.target[0]/.0254,y:a.target[1]/.0254,diameter:a.diameter/.0254,holeDiameter:a.hole/.0254,solderMaskExpansion:{topSolderMask:-a.diameter/2/.0254,bottomSolderMask:-a.diameter/2/.0254}}))throw Error('Via clearance repair failed');for(const r of a.routes){const ps=r.pointsMm;const polygon=eda.pcb_MathPolygon.createPolygon([ps[0][0]/.0254,ps[0][1]/.0254,'L',...ps.slice(1).flatMap(p=>[p[0]/.0254,p[1]/.0254])]);if(!await eda.pcb_PrimitivePolyline.modify(r.id,{polygon,lineWidth:r.widthMm/.0254}))throw Error('Via tail repair failed');}return {target:a.target,routes:a.routes.map(r=>r.id),saved:await eda.pcb_Document.save()};"
(R/'scripts/apply-clearancefix-sim-ground-v14.js').write_text(js,encoding='utf8');(M/'clearancefix-sim-ground-repair-v14.json').write_text(json.dumps(args,indent=2),encoding='utf8');(M/'clearancefix-rerouted-plan-v14.json').write_text(json.dumps(expected,indent=2),encoding='utf8');print('Safe target',x,y,'attached routes',len(rs))
