from pathlib import Path
import json,math,copy
P=Path('PCB');M=P/'manifests'
exec((P/'scripts/router-v13.py').read_text(encoding='utf8').replace('read-pcb-pads-v13.json','smt-proposed-pads-v13.json'))
base=json.loads((M/'hy20-final-routing-source-v13.json').read_text());chosen=json.loads((M/'smt-proposed-routing-check-v13.json').read_text())
changed=set(chosen['changedRoutes']);keep=[r for r in base['routes'] if r['id'] not in changed]
tails=[];jobs=[]
for r in base['routes']:
 if r['id'] not in changed:continue
 ref='D6' if r['id'] in ['1b0a3e249f4e8ef1','8525f9021d2422cd'] else 'Q1'
 old=next(c for c in json.loads((M/'hy20-final-pcb-pads-v13.json').read_text())['result'] if c['ref']==ref)
 seq=r['pointsMm'][:]
 m=next(p for p in old['pads'] if p['net']==r['net'] and min(math.dist(seq[k],(p['x']*.0254,p['y']*.0254)) for k in [0,-1])<.015)
 if math.dist(seq[-1],(m['x']*.0254,m['y']*.0254))<.015:seq.reverse()
 target=next(p for p in pads if p['ref']==ref and p['number']==m['number'])
 if ref=='D6' and r['net']=='GND':continue
 k=next((i for i,q in enumerate(seq[1:],1) if math.dist(q,seq[0])>2),len(seq)-1) if ref=='Q1' else len(seq)-1
 if k<len(seq)-1:tails.append({**r,'id':r['id']+'_tail','pointsMm':seq[k:]})
 jobs.append({'ref':ref,'net':r['net'],'a':(target['x'],target['y'],1),'b':(*seq[k],1),'width':r['widthMm']})
for r in keep+tails:tracks.append({'net':r['net'],'layer':r['layer'],'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2),'points':r['pointsMm']})
vias.extend(base['vias'])
# TVS returns to the ground plane through a nearby dedicated via, not a long ground trace.
p=next(p for p in pads if p['ref']=='D6' and p['net']=='GND')
v=addvia('GND',(p['x'],p['y']-.95),.65,.3,(p['x'],p['y']),1,.3)
assert v is not None
for j in sorted(jobs,key=lambda j:(j['ref']!='Q1',j['net']!='GND',j['net'])):
 ok=addroute(j['net'],j['a'],j['b'],j['width'],(1,))
 if not ok:ok=addroute(j['net'],j['a'],j['b'],j['width'],(1,2,16))
 print(j['ref'],j['net'],ok,flush=True)
 if not ok:raise RuntimeError('Routing failed '+str(j))
result={'routes':keep+tails+new,'vias':base['vias']+newvias}
(M/'smt-rerouted-plan-v13.json').write_text(json.dumps(result,indent=2),encoding='utf8')
(M/'smt-reroute-diff-v13.json').write_text(json.dumps({'deleteRoutes':list(changed),'tails':tails,'newRoutes':new,'newVias':newvias,'jobs':jobs},indent=2),encoding='utf8')
print('Final',len(result['routes']),len(result['vias']))
