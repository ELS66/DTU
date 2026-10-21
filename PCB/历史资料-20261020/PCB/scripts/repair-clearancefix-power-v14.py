from pathlib import Path
import json,math
s=Path('PCB/scripts/router-v13.py').read_text(encoding='utf8').replace('read-pcb-pads-v13.json','clearancefix-staged-pads-v14.json').replace('(4,66),(56,66)','(4,71),(56,71)').replace('ny=701','ny=751').replace('69.5','74.5').replace('69.25','74.25');exec(s)
M=P/'manifests';plan=json.loads((M/'clearancefix-rerouted-plan-v14.json').read_text(encoding='utf8'));diff=json.loads((M/'clearancefix-routing-diff-v14.json').read_text(encoding='utf8'))
assert len(diff['failed'])==2 and all(r['net']=='VDD_4G' for r in diff['failed'])
old=diff['failed'][0]['pointsMm'][0];v=next(v for v in plan['vias'] if v['net']=='VDD_4G' and math.dist((v['x'],v['y']),old)<.005)
target=(7.0,51.725);v['x'],v['y']=target;diff['viaTargets'][v['id']]=list(target)
for r in plan['routes']:
 assert not any(math.dist(p,old)<.005 for p in r['pointsMm']),('Existing branch needs moving',r['id'])
 tracks.append({'net':r['net'],'layer':r['layer'],'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2),'points':r['pointsMm']})
vias.extend(plan['vias'])
for v2 in plan['vias']:
 if v2['id']==v['id']:continue
 assert math.dist(target,(v2['x'],v2['y']))>(v2['diameter']+v['diameter'])/2+.154
for r in diff['failed']:
 aa,bb=r['pointsMm'][0],r['pointsMm'][-1]
 aa=list(target) if math.dist(aa,old)<.005 else aa;bb=list(target) if math.dist(bb,old)<.005 else bb
 layer=r['layer'];w=r['widthMm'];ok=addline(r['net'],layer,[aa,bb],w) or addroute(r['net'],(*aa,layer),(*bb,layer),w,(layer,))
 print('Power',r['id'],layer,w,ok,flush=True)
 if not ok:raise RuntimeError('Full-width power route still blocked')
start=len(diff['newRoutes'])
for i,r in enumerate(new):plan['routes'].append({**r,'id':'clearance_new_'+str(start+i)})
for i,v in enumerate(newvias):plan['vias'].append({**v,'id':'clearance_via_'+str(len(diff['newVias'])+i)})
diff['newRoutes']+=new;diff['newVias']+=newvias;diff['failed']=[]
(M/'clearancefix-rerouted-plan-v14.json').write_text(json.dumps(plan,indent=2),encoding='utf8');(M/'clearancefix-routing-diff-v14.json').write_text(json.dumps(diff,indent=2),encoding='utf8');print('Final',len(plan['routes']),len(plan['vias']),flush=True)
