from pathlib import Path
import copy,json,math
P=Path('PCB')
exec((P/'scripts/router-v13.py').read_text(encoding='utf8').replace('read-pcb-pads-v13.json','hy20-proposed-pads-v13.json'))
from shapely.strtree import STRtree
base=json.loads((P/'manifests/routing-optimized-source-v13.json').read_text());plan=copy.deepcopy(base)
removed_power_vias=[v for v in plan['vias'] if v['net']=='VIN_IN' and v['y']<6.1]
assert len(removed_power_vias)==6
for v in removed_power_vias:
 touching={r['layer'] for r in base['routes'] if r['net']==v['net'] and LineString(r['pointsMm']).distance(Point(v['x'],v['y']))<=r['widthMm']/2+v['diameter']/2+.001}
 assert touching=={1},('Power via is used on another layer',v,touching)
plan['routes']=[r for r in plan['routes'] if not(r['net'] in ['VIN_IN','GND'] and min(q[1] for q in r['pointsMm'])<6.1)]
plan['vias']=[v for v in plan['vias'] if v not in removed_power_vias]
ground=[]
for v in plan['vias']:
 if v['net']=='GND' and v['y']<6.1:
  assert abs(v['y']-5.8)<.001
  v['y']=2.2;v.pop('id',None);ground.append(v)
assert len(ground)==6
old=(18.6000009,8.30000118);target=(17.5,9.0);moved=[]
for v in plan['vias']:
 if v['net']=='RS485_B_EXT' and math.dist((v['x'],v['y']),old)<.002:
  v['x'],v['y']=target;v.pop('id',None);moved.append(v)
assert len(moved)==1
for r in plan['routes']:
 if r['net']=='RS485_B_EXT' and any(math.dist(p,old)<.002 for p in r['pointsMm']):
  r['pointsMm']=[list(target) if math.dist(p,old)<.002 else p for p in r['pointsMm']];r.pop('id',None)
sig=lambda ref,num:next(p for p in pads if p['ref']==ref and p['number']==num)
def add(n,pts,w):plan['routes'].append({'net':n,'layer':1,'widthMm':w,'pointsMm':[list(q) for q in pts]})
add('VIN_IN',[(sig('J1','1')['x'],1.1),(sig('J3','1')['x'],1.1)],.8)
for ref in ['J1','J2','J3']:
 p=sig(ref,'1');add('VIN_IN',[(p['x'],p['y']),(p['x'],1.1)],.8)
 p=sig(ref,'4');vs=sorted(ground,key=lambda v:math.dist((v['x'],v['y']),(p['x'],2.2)))[:2]
 add('GND',[(p['x'],p['y']),(vs[0]['x'],vs[0]['y'])],.6);add('GND',[(vs[0]['x'],vs[0]['y']),(vs[1]['x'],vs[1]['y'])],.6)
obs=[]
for p in pads:obs.append({'net':p['net'],'ls':{1,2,15,16} if p['layer']==12 else {p['layer']},'geom':p['geom'],'type':'pad','id':p['ref']+':'+p['number']})
for i,r in enumerate(plan['routes']):obs.append({'net':r['net'],'ls':{r['layer']},'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2),'type':'track','id':'t'+str(i)})
for i,v in enumerate(plan['vias']):obs.append({'net':v['net'],'ls':{1,2,15,16},'geom':Point(v['x'],v['y']).buffer(v['diameter']/2),'type':'via','id':'v'+str(i)})
tree=STRtree([o['geom'] for o in obs]);bad=[];mind=100
for i,o in enumerate(obs):
 for j in tree.query(o['geom'].buffer(.16)):
  q=obs[j]
  if j>=i or not o['ls']&q['ls'] or (o['net'] and o['net']==q['net']):continue
  d=o['geom'].distance(q['geom']);mind=min(mind,d);limit=.149 if o['type']==q['type']=='pad' else .1528
  if d<limit:bad.append({'a':o['id'],'b':q['id'],'an':o['net'],'bn':q['net'],'distance':d})
vip=[]
for p in pads:
 if p['ref'] not in ['J1','J2','J3']:continue
 for v in plan['vias']:
  if p['geom'].distance(Point(v['x'],v['y']))<v['diameter']/2+.10:vip.append([p['ref'],p['number'],v])
result={'conflicts':bad,'minCopperClearanceMm':mind,'viasNearConnectorPads':vip,'oldVias':len(base['vias']),'newVias':len(plan['vias']),'removedTopOnlyPowerVias':removed_power_vias,'relocatedGroundVias':6,'bodyMinimumYmm':5-169.685*.0254}
(P/'manifests/hy20-local-routing-v13.json').write_text(json.dumps(plan,indent=2));(P/'manifests/hy20-local-routing-check-v13.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
if bad or vip:raise SystemExit(1)
