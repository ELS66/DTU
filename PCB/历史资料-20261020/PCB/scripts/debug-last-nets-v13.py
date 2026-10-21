from pathlib import Path
s=Path('PCB/scripts/router-v13.py').read_text(encoding='utf8').replace('if not starts or not targets:return None','if not starts or not targets:\n  print("NOSEED",net,a,b,len(starts),len(targets),flush=True);return None').replace('if count>limit:return None','if count>limit:\n   print("LIMIT",net,a,b,count,flush=True);return None').replace('if line.distance(obs[l])<width/2+.153:return None','if line.distance(obs[l])<width/2+.153:\n     print("VALIDATION",net,line.distance(obs[l]),width/2+.153,flush=True);return None');exec(s)
load_plan(P/'manifests/surgical2-routing-v13.json')
exec('def groups(net):'+Path('PCB/scripts/plan-remaining-routing-v13.py').read_text(encoding='utf8').split('def groups(net):')[1].split('power={')[0])
for net in ['RS485_B','TTL_RX_EXT']:
 gs=groups(net);print(net,'groups',len(gs),flush=True)
 for g in gs:
  print('Representative',g[0],'vias',[v for v in vias if v['net']==net and any(math.dist((v['x'],v['y']),p[:2])<.01 for p in g)],flush=True)
 a=min([v for v in vias if v['net']==net],key=lambda v:v['x']);g1=next(g for g in gs if any(math.dist((a['x'],a['y']),q[:2])<.01 for q in g));g2=next(g for g in gs if g is not g1);vs=[v for v in vias if v['net']==net and any(math.dist((v['x'],v['y']),q[:2])<.01 for q in g2)]
 b=vs[0] if vs else {'x':g2[0][0],'y':g2[0][1]}
 print('TRY bottom',(a['x'],a['y']),(b['x'],b['y']),flush=True)
 rr=route(net,(a['x'],a['y'],2),(b['x'],b['y'],2),.1524,(2,16),limit=200000);print('result',None if rr is None else len(rr[0]),flush=True)
