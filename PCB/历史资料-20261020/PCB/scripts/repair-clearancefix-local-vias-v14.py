from pathlib import Path
import json,math
s=Path('PCB/scripts/router-v13.py').read_text(encoding='utf8').replace('read-pcb-pads-v13.json','clearancefix-staged-pads-v14.json').replace('(4,66),(56,66)','(4,71),(56,71)').replace('ny=701','ny=751').replace('69.5','74.5').replace('69.25','74.25');exec(s)
M=P/'manifests';plan=json.loads((M/'clearancefix-rerouted-plan-v14.json').read_text(encoding='utf8'));targets=['d3051dab07d65649','abfcf2d8581e31d5','393063f154125e13'];changes=[]
for v in plan['vias']:
 if v['id'] not in targets:continue
 old=(v['x'],v['y']);opts=[]
 for radius in [.1,.15,.2,.3,.4,.5,.7,1,1.5,2]:
  for i in range(64):
   x=round(old[0]+radius*math.cos(i*math.pi/32),3);y=round(old[1]+radius*math.sin(i*math.pi/32),3);pt=Point(x,y)
   if min(pt.distance(p['geom']) for p in pads)<.435:continue
   if any(pt.distance(h)<.23 for h in holes):continue
   if any(math.dist((x,y),(u['x'],u['y']))<(v['diameter']+u['diameter'])/2+.16 for u in plan['vias'] if u['id']!=v['id']):continue
   if any(pt.distance(LineString(r['pointsMm']))<v['diameter']/2+r['widthMm']/2+.16 for r in plan['routes'] if r['net']!=v['net']):continue
   opts.append((math.dist((x,y),old),x,y))
  if opts:break
 if not opts:raise RuntimeError('No corrected site '+v['id'])
 _,x,y=min(opts);v['x'],v['y']=x,y;changes.append({'id':v['id'],'net':v['net'],'from':list(old),'to':[x,y]})
selected=[];kept=[]
for r in plan['routes']:
 changed=False
 for pt in r['pointsMm']:
  for move in changes:
   if r['net']==move['net'] and math.dist(pt,move['from'])<.006:pt[:]=move['to'];changed=True
 if changed:selected.append(r)
 else:kept.append(r)
for r in kept:tracks.append({'net':r['net'],'layer':r['layer'],'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2),'points':r['pointsMm']})
vias.extend(plan['vias'])
for r in selected:
 aa,bb=r['pointsMm'][0],r['pointsMm'][-1];w=r['widthMm'];lay=r['layer']
 ok=addline(r['net'],lay,[aa,bb],w) or addroute(r['net'],(*aa,lay),(*bb,lay),w,(lay,)) or addroute(r['net'],(*aa,lay),(*bb,lay),w,tuple(dict.fromkeys([lay,1,2,16])))
 print(r['net'],r['id'],ok,flush=True)
 if not ok:raise RuntimeError('Via tail reroute failed')
plan['routes']=kept+[{**r,'id':'clearance_tail_'+str(i)} for i,r in enumerate(new)]
plan['vias'] +=[{**v,'id':'clearance_tail_via_'+str(i)} for i,v in enumerate(newvias)]
(M/'clearancefix-local-via-repairs-v14.json').write_text(json.dumps(changes,indent=2),encoding='utf8');(M/'clearancefix-rerouted-plan-v14.json').write_text(json.dumps(plan,indent=2),encoding='utf8');print('Final',len(plan['routes']),len(plan['vias']),flush=True)
