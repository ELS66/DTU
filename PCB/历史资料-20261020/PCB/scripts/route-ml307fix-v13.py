"""Plan local rerouting around corrected ML307R outer lands; no live changes."""
from pathlib import Path
import json,math,copy
exec(Path('PCB/scripts/router-v13.py').read_text(encoding='utf8').replace('read-pcb-pads-v13.json','ml307fix-proposed-pads-v13.json'))
M=P/'manifests';base=json.loads((M/'lead-hole-actual-routing-v13.json').read_text(encoding='utf8'));oldcs=json.loads((M/'silkclean-pcb-pads-v13.json').read_text(encoding='utf8'))['result'];oldby={c['ref']:c for c in oldcs}
via_targets={'078d67cc67266197':(9.9,42.0),'c82ab33a1f65480a':(12.25,61.9),'c9cfe2f76e16b555':(9.4,65.1),'2662308277b0d568':(16.8,64.6),'f2eb9cd5d27ee5dc':(24.5,61.7),'2cdd2758287c7fb4':(21.0,61.7),'d3b2388593d4b626':(7.05,50.825),'c0299af4fcc5f953':(7.05,51.925),'d34fbe859532576a':(7.05,55.225),'fdd329252a28af53':(7.05,56.325),'c5b5235b7ff31b5a':(12.075,57.8),'31780437ea8d2598':(19.775,57.8),'fd6c2fb7019faf50':(21.1,42.1),'9ca3c30c2d0b93b8':(25.9,45.3)}
# Find nearby via sites with >=0.44mm center-to-land clearance, including same-net lands.
all_pad_union=unary_union([p['geom'] for p in pads])
chosen={}
for vid,target in via_targets.items():
 opts=[]
 for ix in range(-20,21):
  for iy in range(-20,21):
   x=round(target[0]+ix*.05,3);y=round(target[1]+iy*.05,3);pt=Point(x,y)
   if not(.75<x<59.25 and .75<y<69.25):continue
   if pt.distance(all_pad_union)<.44:continue
   if any(pt.distance(h)<.225 for h in holes):continue
   if any(math.hypot(x-v['x'],y-v['y'])<.5 for v in base['vias'] if v['id']!=vid and v['id'] not in via_targets):continue
   if any(math.dist((x,y),q)<.5 for q in chosen.values()):continue
   opts.append((math.dist((x,y),target),x,y))
 if not opts:raise RuntimeError('No via site '+vid)
 _,x,y=min(opts);chosen[vid]=(x,y)
via_targets=chosen
# Deliberate pad endpoint updates; other existing route points retain original coordinates.
pointmoves=[]
for c in cs:
 old=oldby[c['ref']]
 for p in c['pads']:
  op=next(q for q in old['pads'] if q['id']==p['id'])
  if math.hypot(p['x']-op['x'],p['y']-op['y'])*.0254>.01:pointmoves.append((p['net'],(op['x']*.0254,op['y']*.0254),(p['x']*.0254,p['y']*.0254)))
for v in base['vias']:
 if v['id'] in via_targets:pointmoves.append((v['net'],(v['x'],v['y']),via_targets[v['id']]))
via_plan=[{**v,**({'x':via_targets[v['id']][0],'y':via_targets[v['id']][1]} if v['id'] in via_targets else {})} for v in base['vias']]
# Report proposed via-to-pad problems before routing.
for v in via_plan:
 if v['id'] not in via_targets:continue
 near=min((Point(v['x'],v['y']).distance(p['geom']),p['ref'],p['number'],p['net']) for p in pads)
 foreign=min(Point(v['x'],v['y']).distance(p['geom']) for p in pads if p['net']!=v['net'])
 print('VIA',v['id'],v['net'],round(near[0],3),near[1:3],'foreign',round(foreign,3),flush=True)
 if foreign<.225+.154:raise RuntimeError('Via position collides with pad '+v['id'])
selected={};kept=[]
rf={'LTE_ANT','LTE_RF_FEED'}
for r in base['routes']:
 seq=copy.deepcopy(r['pointsMm']);modified=False
 for i in [0,-1]:
  for net,old,newpt in pointmoves:
   if net==r['net'] and math.dist(seq[i],old)<.02:seq[i]=list(newpt);modified=True;break
 g=LineString(seq).buffer(r['widthMm']/2)
 bad=any(g.distance(p['geom'])<.154 for p in pads if p['net']!=r['net'] and p['layer'] in [r['layer'],12]) or any(g.distance(Point(v['x'],v['y']).buffer(v['diameter']/2))<.154 for v in via_plan if v['net']!=r['net'])
 if modified or bad or r['net'] in rf:selected[r['id']]={**r,'pointsMm':seq}
 else:kept.append(r)
print('SELECTED',len(selected),dict(__import__('collections').Counter(r['net'] for r in selected.values())),flush=True)
# Keep copper clear and retain the two known baseline numerical threshold pairs.
for r in kept:tracks.append({'net':r['net'],'layer':r['layer'],'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2),'points':r['pointsMm']})
vias.extend(via_plan)
# Compact RF paths, all Top; dimensions preserve original0.35mm trace width pending stackup impedance verification.
rf_jobs=[('LTE_ANT',xy('U2','35'),xy('R50','1')),('LTE_ANT',xy('R50','1'),xy('C50','1')),('LTE_RF_FEED',xy('R50','2'),xy('J5','2')),('LTE_RF_FEED',xy('J5','2'),xy('D10','1')),('LTE_RF_FEED',xy('D10','1'),xy('C51','1'))]
for net,aa,bb in rf_jobs:
 if not addline(net,1,[aa,bb],.35):
  if not addroute(net,(*aa,1),(*bb,1),.35,(1,)):raise RuntimeError('RF path failed '+net+str((aa,bb)))
print('RF done',flush=True)
jobs=[r for r in selected.values() if r['net'] not in rf];jobs.sort(key=lambda r:(not ('USB' in r['net']),r['net'] not in ['VDD_4G','GND'],r['net']=='GND',-r['widthMm'],len(r['pointsMm'])))
failed=[]
for n,r in enumerate(jobs):
 aa,bb=r['pointsMm'][0],r['pointsMm'][-1];layer=r['layer'];w=r['widthMm']
 if math.dist(aa,bb)<.01:continue
 if addline(r['net'],layer,[aa,bb],w):ok=True
 elif addroute(r['net'],(*aa,layer),(*bb,layer),w,(layer,)):ok=True
 elif r['net'] in ['LTE_USB_DP','LTE_USB_DM','LTE_USB_DP_EXT','LTE_USB_DM_EXT']:
  ok=addroute(r['net'],(*aa,layer),(*bb,layer),w,tuple(dict.fromkeys([layer,1,2,16])))
 else:ok=addroute(r['net'],(*aa,layer),(*bb,layer),w,tuple(dict.fromkeys([layer,1,2,16])))
 print(n,r['net'],r['id'],ok,'addedVias',len(newvias),flush=True)
 if not ok:failed.append(r)
result={'routes':kept+[{**r,'id':'ml307_new_'+str(i)} for i,r in enumerate(new)],'vias':via_plan+[{**v,'id':'ml307_via_'+str(i)} for i,v in enumerate(newvias)]}
(M/'ml307fix-rerouted-plan-v13.json').write_text(json.dumps(result,indent=2),encoding='utf8');(M/'ml307fix-routing-diff-v13.json').write_text(json.dumps({'removedRoutes':list(selected),'viaTargets':via_targets,'newRoutes':new,'newVias':newvias,'failed':failed},indent=2),encoding='utf8')
print('RESULT',len(result['routes']),len(result['vias']),'FAILED',len(failed))
