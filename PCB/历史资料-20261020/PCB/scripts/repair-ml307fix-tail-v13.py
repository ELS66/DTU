from pathlib import Path
import json,math,copy
exec(Path('PCB/scripts/router-v13.py').read_text(encoding='utf8').replace('read-pcb-pads-v13.json','ml307fix-proposed-pads-v13.json'))
M=P/'manifests';plan=json.loads((M/'ml307fix-rerouted-plan-v13.json').read_text(encoding='utf8'));diff=json.loads((M/'ml307fix-routing-diff-v13.json').read_text(encoding='utf8'))
for r in plan['routes']:tracks.append({'net':r['net'],'layer':r['layer'],'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2),'points':r['pointsMm']})
vias.extend(plan['vias'])
power=next(r for r in diff['failed'] if r['net']=='VDD_4G');aa,bb=power['pointsMm'][0],power['pointsMm'][-1];ok=False
for w in [.65,.6,.5]:
 if addroute('VDD_4G',(*aa,1),(*bb,1),w,(1,)):print('Power routed',w,flush=True);ok=True;break
if not ok:raise RuntimeError('Power branch failed')
pwr=[r for r in diff['failed'] if r['net']=='LTE_PWRKEY'];aa=pwr[0]['pointsMm'][0];bb=pwr[-1]['pointsMm'][-1]
if not addroute('LTE_PWRKEY',(*aa,1),(*bb,1),.1524,(1,)):
 if not addroute('LTE_PWRKEY',(*aa,1),(*bb,1),.1524,(1,2,16)):raise RuntimeError('PWRKEY route failed')
print('PWRKEY routed',flush=True)
start=len(diff['newRoutes'])
for i,r in enumerate(new):plan['routes'].append({**r,'id':'ml307_new_'+str(start+i)})
for i,v in enumerate(newvias):plan['vias'].append({**v,'id':'ml307_via_'+str(len(diff['newVias'])+i)})
diff['newRoutes']+=new;diff['newVias']+=newvias;diff['failed']=[];diff['removedArtificialJunctionMm']=[24.2,43.0];diff['powerBranchWidthMm']=new[0]['widthMm']
(M/'ml307fix-rerouted-plan-v13.json').write_text(json.dumps(plan,indent=2),encoding='utf8');(M/'ml307fix-routing-diff-v13.json').write_text(json.dumps(diff,indent=2),encoding='utf8');print('Final',len(plan['routes']),len(plan['vias']))
s=Path('PCB/scripts/check-routing-opt-actual-copper-v13.py').read_text(encoding='utf8').replace('read-pcb-pads-before-opt-v13.json','ml307fix-proposed-pads-v13.json').replace('routing-optimized-source-v13.json','ml307fix-rerouted-plan-v13.json').replace('routing-opt-actual-copper-check-v13.json','ml307fix-proposed-copper-check-v13.json');exec(s)
