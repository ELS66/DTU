from pathlib import Path
exec(Path('PCB/scripts/router-v12.py').read_text(encoding='utf-8'))
failed=[]
for net in ['LTE_ANT','LTE_RF_FEED']:
 ps=[p for p in pads if p['net']==net];connected=[ps[0]];rest=ps[1:]
 while rest:
  _,i,j=min((math.dist((a['x'],a['y']),(b['x'],b['y'])),i,j) for i,a in enumerate(connected) for j,b in enumerate(rest));a=connected[i];b=rest.pop(j)
  if not addroute(net,(a['x'],a['y'],1),(b['x'],b['y'],1),.32,(1,)):failed.append([net,a['ref'],b['ref']])
  connected.append(b)
 print(net,'completed',flush=True)
save_plan('rf-routing-v12',failed)
