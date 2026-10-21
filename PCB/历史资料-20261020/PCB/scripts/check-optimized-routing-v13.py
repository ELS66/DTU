from pathlib import Path
src=Path('PCB/scripts/optimize-routing-v13.py').read_text(encoding='utf8').split('protected=')[0]
import sys
sys.argv=['check','--resume']
exec(src)
before=json.loads(BASE.read_text())
removed=[]
def padgroups(net,rs,vs):
 return sum(any(o.get('pad') for o in g) for g in groups(net,rs,vs))
protected={'GND','VDD_3V3','VDD_4G','VIN_IN','VIN_DIODE','VIN_PROT','SIM_VDD','LTE_VDD_EXT','LTE_SW','LTE_BST','LTE_FB','MCU_LDO_FB','LTE_ANT','LTE_RF_FEED','232_VMINUS'}
redundant_tracks=[]
for r in sorted(plan['routes'],key=lambda r:-LineString(r['pointsMm']).length):
 if r['net'] in protected or 'USB' in r['net'] or r['net'].startswith('232_C'):continue
 rs=[q for q in plan['routes'] if q is not r]
 if padgroups(r['net'],rs,plan['vias'])<=padgroups(r['net'],plan['routes'],plan['vias']):
  redundant_tracks.append(r);plan['routes']=rs
print('Redundant signal trace primitives removed',len(redundant_tracks),flush=True)
for v in list(plan['vias']):
 if v['net'] in protected or 'USB' in v['net'] or v['net'].startswith('232_C'):continue
 vs=[q for q in plan['vias'] if q is not v]
 if padgroups(v['net'],plan['routes'],vs)<=padgroups(v['net'],plan['routes'],plan['vias']):
  removed.append(v);plan['vias']=vs
print('Redundant non-ground vias removed',len(removed),flush=True)
floating=[]
for net in sorted({r['net'] for r in plan['routes'] if r['net'] not in protected and 'USB' not in r['net'] and not r['net'].startswith('232_C')}):
 for g in groups(net,plan['routes'],plan['vias']):
  if any(o.get('pad') for o in g):continue
  island=unary_union([o['geom'] for o in g])
  drop=[r for r in plan['routes'] if r['net']==net and LineString(r['pointsMm']).buffer(r['widthMm']/2).distance(island)<.001]
  # Layer-aware membership: an isolated same-net crossing in another layer must remain.
  drop=[r for r in drop if any(r['layer'] in o['ls'] and LineString(r['pointsMm']).buffer(r['widthMm']/2).distance(o['geom'])<.001 for o in g)]
  for r in drop:plan['routes'].remove(r)
  floating.extend(drop)
print('Floating trace primitives removed',len(floating),flush=True)
OUT.write_text(json.dumps(plan,indent=2))
(P/'manifests/routing-redundant-vias-v13.json').write_text(json.dumps(removed,indent=2))
badconnect=[]
for n in sorted({p['net'] for p in pads if p['net'] and p['net']!='GND'}):
 a=padgroups(n,before['routes'],before['vias']);b=padgroups(n,plan['routes'],plan['vias'])
 if b>a:badconnect.append({'net':n,'beforeGroups':a,'afterGroups':b})
obs=[]
for p in pads:obs.append({'net':p['net'],'layers':{1,2,15,16} if p['layer']==12 else {p['layer']},'geom':p['geom'],'type':'pad','id':p['ref']+':'+p['number']})
for i,r in enumerate(plan['routes']):obs.append({'net':r['net'],'layers':{r['layer']},'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2),'type':'track','id':f't{i}'})
for i,v in enumerate(plan['vias']):obs.append({'net':v['net'],'layers':{1,2,15,16},'geom':Point(v['x'],v['y']).buffer(v['diameter']/2),'type':'via','id':f'v{i}'})
tr=STRtree([p['geom'] for p in obs]);bad=[];min_dist=10
for i,p in enumerate(obs):
 for j in tr.query(p['geom'].buffer(.16)):
  q=obs[j]
  if j>=i or not p['layers']&q['layers'] or (p['net'] and p['net']==q['net']):continue
  d=p['geom'].distance(q['geom']);min_dist=min(min_dist,d);limit=.149 if p['type']==q['type']=='pad' else .1528
  if d<limit:bad.append({'a':p['id'],'b':q['id'],'an':p['net'],'bn':q['net'],'distanceMm':round(d,6)})
print('Connectivity regressions',badconnect,'copper conflicts',len(bad),'minimum',min_dist,'vias',len(plan['vias']),flush=True)
result={'beforeVias':len(before['vias']),'afterVias':len(plan['vias']),'removedRedundantVias':len(removed),'removedRedundantSignalTraces':len(redundant_tracks),'removedFloatingTraces':len(floating),'connectivityRegressions':badconnect,'conflicts':bad,'minimumClearanceMm':min_dist}
(P/'manifests/routing-optimization-check-v13.json').write_text(json.dumps(result,indent=2))
if badconnect or bad:raise SystemExit(1)

