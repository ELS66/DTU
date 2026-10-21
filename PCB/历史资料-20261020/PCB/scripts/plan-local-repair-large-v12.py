from pathlib import Path
exec(Path('PCB/scripts/load-native-routing-large-v12.py').read_text(encoding='utf-8-sig').replace('routing-power-large-v12.json','routing-resume-large-v12.json'))
vias[:]=[v for v in vias if not(v['net']=='VDD_4G' and math.dist((v['x'],v['y']),(26.2,27.1))<.001)]
exec('def groups(net):'+Path('PCB/scripts/plan-remaining-routing-large-v12.py').read_text(encoding='utf-8-sig').split('def groups(net):')[1].split('power={')[0])
step=.05;nx=1201;ny=1401
old_route=route
def route(net,a,b,width=.1524,allowed=(1,2,16),limit=180000):
 return old_route(net,a,b,width,allowed,limit)
failed=[]
for net in ['SIM_RST_M','SIM_DATA_M','LTE_PWRKEY','LTE_RX_SER','MCU_LTE_PWRKEY','232_RIN','MCU_485_DE','SIM_DET','SIM_DATA','FIELD_TX']:
 gs=groups(net)
 while len(gs)>1:
  candidates=sorted((math.dist(a[:2],b[:2]),i,j,a,b) for i,g in enumerate(gs) for j,h in enumerate(gs[:i]) for a in g for b in h)
  success=False
  for _,i,j,a,b in candidates[:12]:
   if a[2]==b[2] and addline(net,a[2],[a[:2],b[:2]]):success=True
   elif addroute(net,a,b):success=True
   if success:
    gs[j].extend(gs[i]);gs.pop(i);break
  if not success:
   failed.append({'net':net,'groupsRemaining':len(gs),'representatives':[g[0] for g in gs]});break
 print(net,'groups',len(gs),'routes',len(new),'vias',len(newvias),flush=True)
 save_plan('local-repair-large-v12',failed)
