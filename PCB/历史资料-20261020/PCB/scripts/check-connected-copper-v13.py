from pathlib import Path
exec(Path('PCB/scripts/router-v13.py').read_text(encoding='utf8'))
from shapely.strtree import STRtree
plan=json.load(open(P/'manifests/connected-routing-v13.json',encoding='utf8'));obs=[]
for p in pads:obs.append({'net':p['net'],'layers':{1,2,15,16} if p['layer']==12 else {p['layer']},'geom':p['geom'],'type':'pad','id':p['ref']+':'+p['number']})
for i,r in enumerate(plan['routes']):obs.append({'net':r['net'],'layers':{r['layer']},'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2),'type':'track','id':f't{i}'})
for i,v in enumerate(plan['vias']):obs.append({'net':v['net'],'layers':{1,2,15,16},'geom':Point(v['x'],v['y']).buffer(v['diameter']/2),'type':'via','id':f'v{i}'})
tr=STRtree([p['geom'] for p in obs]);bad=[];min_dist=10
for i,p in enumerate(obs):
 for j in tr.query(p['geom'].buffer(.16)):
  q=obs[j]
  if j>=i or not p['layers']&q['layers'] or (p['net'] and p['net']==q['net']):continue
  d=p['geom'].distance(q['geom']);min_dist=min(min_dist,d);limit=.149 if p['type']==q['type']=='pad' else .1528
  if d<limit:bad.append({'a':p['id'],'b':q['id'],'an':p['net'],'bn':q['net'],'at':p['type'],'bt':q['type'],'distanceMm':round(d,6)})
print('Copper conflicts',len(bad),'minimum',min_dist,'first',bad[:25]);(P/'manifests/connected-copper-check-v13.json').write_text(json.dumps({'conflicts':bad,'minimumClearanceMm':min_dist},indent=2))
