from pathlib import Path
import json,math,copy
exec(Path('PCB/scripts/router-v13.py').read_text(encoding='utf8').replace('read-pcb-pads-v13.json','silkclean-pcb-pads-v13.json'))
M=P/'manifests';base=json.loads((M/'exposure-fixed-actual-routing-v13.json').read_text(encoding='utf8'));v0=next(v for v in base['vias'] if v['id']=='bd31757caf9c21db');q0=next(v for v in base['vias'] if v['id']=='026b68367e7fffbc')
selected=[r for r in base['routes'] if any(math.dist(p,(v0['x'],v0['y']))<.01 for p in r['pointsMm'])];delete={'7f346228493bc1ec','28a99dd71c00d902'}
vnew=(20.525,26.675);qnew=(26.7,40.925);updates=[]
qroute=next(r for r in base['routes'] if r['id']=='e2a02a13e168d820');updates.append({**qroute,'pointsMm':[qroute['pointsMm'][0],list(qnew)]})
fixed=[r for r in base['routes'] if r not in selected and r['id']!=qroute['id'] and r['id']!='fb2d950154672c84']+updates[:]
for r in fixed:tracks.append({'net':r['net'],'layer':r['layer'],'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2),'points':r['pointsMm']})
for v in base['vias']:vias.append({**v,**({'x':vnew[0],'y':vnew[1]} if v['id']==v0['id'] else {'x':qnew[0],'y':qnew[1]} if v['id']==q0['id'] else {})})
top=next(r for r in selected if r['id']=='6c13cfc7ca898ee8');r2=next(r for r in selected if r['layer']==2);r16=next(r for r in selected if r['layer']==16)
jobs=[(top,top['pointsMm'][-1],[],1),(r2,r2['pointsMm'][-2],list(reversed(r2['pointsMm'][:-1])),2),(r16,r16['pointsMm'][1],r16['pointsMm'][1:],16)]
for old,target,tail,layer in jobs:
 res=route('SIM_VDD',(*vnew,layer),(*target,layer),old['widthMm'],(layer,),120000)
 if res is None:raise RuntimeError('Cannot route '+old['id'])
 rs,vs=res;assert len(rs)==1 and not vs
 seq=rs[0]['pointsMm'];seq+=tail[1:] if tail else []
 changed={**old,'pointsMm':seq};updates.append(changed);tracks.append({'net':old['net'],'layer':layer,'geom':LineString(seq).buffer(old['widthMm']/2),'points':seq});print('Routed',old['id'],layer,'points',len(seq),flush=True)
clk=next(r for r in base['routes'] if r['id']=='fb2d950154672c84')
res=route('SIM_CLK',(*clk['pointsMm'][0],1),(*clk['pointsMm'][-1],1),clk['widthMm'],(1,),120000)
if res is None:raise RuntimeError('Cannot reroute SIM_CLK')
rs,vs=res;assert len(rs)==1 and not vs
updates.append({**clk,'pointsMm':rs[0]['pointsMm']});print('SIM_CLK routed',len(rs[0]['pointsMm']),flush=True)
plan={'routes':[r for r in base['routes'] if r['id'] not in delete and r['id'] not in {q['id'] for q in updates}]+updates,'vias':vias}
(M/'lead-hole-proposed-plan-v13.json').write_text(json.dumps(plan,indent=2));(M/'lead-hole-proposed-changes-v13.json').write_text(json.dumps({'deleteRoutes':sorted(delete),'updatedRoutes':updates,'movedVias':[{'id':v0['id'],'from':[v0['x'],v0['y']],'to':vnew},{'id':q0['id'],'from':[q0['x'],q0['y']],'to':qnew}]},indent=2))
print('Planned',len(plan['routes']),len(plan['vias']))
