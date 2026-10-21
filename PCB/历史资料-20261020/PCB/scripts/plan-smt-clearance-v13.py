from pathlib import Path
import json,copy,math
P=Path('PCB');M=P/'manifests'
cs=json.loads((M/'hy20-final-pcb-pads-v13.json').read_text(encoding='utf8'))['result']
shifts={'D6':(1.25,-7.4),'Q1':(-.5,0)}
original=copy.deepcopy(cs)
for c in cs:
 if c['ref'] in shifts:
  dx,dy=shifts[c['ref']];c['x']+=dx/.0254;c['y']+=dy/.0254
  for p in c['pads']:p['x']+=dx/.0254;p['y']+=dy/.0254
(M/'smt-proposed-pads-v13.json').write_text(json.dumps({'result':cs},indent=2),encoding='utf8')
exec((P/'scripts/router-v13.py').read_text(encoding='utf8').replace('read-pcb-pads-v13.json','smt-proposed-pads-v13.json'))
from shapely.strtree import STRtree
plan=json.loads((M/'hy20-final-routing-source-v13.json').read_text());oldplan=copy.deepcopy(plan)
moves=[]
for c in original:
 if c['ref'] in shifts:
  dx,dy=shifts[c['ref']]
  for p in c['pads']:
   moves.append({'ref':c['ref'],'number':p['number'],'net':p['net'],'old':[p['x']*.0254,p['y']*.0254],'new':[p['x']*.0254+dx,p['y']*.0254+dy]})
changed=[]
for r in plan['routes']:
 if r['layer']!=1:continue
 modified=False
 for k in [0,-1]:
  for m in moves:
   if r['net']==m['net'] and math.dist(r['pointsMm'][k],m['old'])<.015:
    r['pointsMm'][k]=m['new'];modified=True;break
 if modified:changed.append(r['id'])
def conflicts(plan):
 obs=[]
 for p in pads:obs.append({'net':p['net'],'layers':{1,2,15,16} if p['layer']==12 else {p['layer']},'geom':p['geom'],'type':'pad','id':p['ref']+':'+p['number']})
 for r in plan['routes']:obs.append({'net':r['net'],'layers':{r['layer']},'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2),'type':'track','id':r['id']})
 for v in plan['vias']:obs.append({'net':v['net'],'layers':{1,2,15,16},'geom':Point(v['x'],v['y']).buffer(v['diameter']/2),'type':'via','id':v['id']})
 tr=STRtree([p['geom'] for p in obs]);bad=[]
 for i,p in enumerate(obs):
  for j in tr.query(p['geom'].buffer(.16)):
   q=obs[j]
   if j>=i or not p['layers']&q['layers'] or (p['net'] and p['net']==q['net']):continue
   d=p['geom'].distance(q['geom']);limit=.149 if p['type']==q['type']=='pad' else .1528
   if d<limit:bad.append({'a':p['id'],'b':q['id'],'an':p['net'],'bn':q['net'],'at':p['type'],'bt':q['type'],'distanceMm':d})
 return bad
bad=conflicts(plan)
(M/'smt-proposed-routing-v13.json').write_text(json.dumps(plan,indent=2),encoding='utf8')
(M/'smt-proposed-routing-check-v13.json').write_text(json.dumps({'shiftsMm':shifts,'changedRoutes':changed,'conflicts':bad},indent=2),encoding='utf8')
print(json.dumps({'shifts':shifts,'changedRoutes':changed,'conflicts':bad},indent=2))
