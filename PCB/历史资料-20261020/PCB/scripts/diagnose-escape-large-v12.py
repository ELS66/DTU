from pathlib import Path
exec(Path('PCB/scripts/load-native-routing-large-v12.py').read_text(encoding='utf-8-sig').replace('routing-power-large-v12.json','routing-resume-large-v12.json'))
step=.1;nx=601;ny=701
for net in ['SIM_DATA_M','LTE_PWRKEY','LTE_RX_SER','MCU_LTE_PWRKEY','232_RIN','MCU_485_DE','SIM_DET','SIM_DATA','FIELD_TX']:
 obs={k:obstacles(net,k) for k in layers}
 vm=maskgeom(unary_union(list(obs.values())),.225+.153)
 for p in [p for p in pads if p['net']==net]:
  m=maskgeom(obs[p['layer']],.0762+.153)
  cx,cy=round(p['x']/step),round(p['y']/step);seen=set();q=collections.deque()
  for xx in range(cx-3,cx+4):
   for yy in range(cy-3,cy+4):
    if not m[yy,xx] and LineString([(p['x'],p['y']),(xx*step,yy*step)]).distance(obs[p['layer']])>.0762+.153:q.append((xx,yy));seen.add((xx,yy))
  exits=[]
  while q:
   x,y=q.popleft()
   if not vm[y,x]:exits.append((x*step,y*step))
   if len(seen)>12000:break
   for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
    xx,yy=x+dx,y+dy
    if 0<xx<nx-1 and 0<yy<ny-1 and abs(xx-cx)<55 and abs(yy-cy)<55 and not m[yy,xx] and (xx,yy) not in seen:seen.add((xx,yy));q.append((xx,yy))
  print(net,p['ref'],p['number'],'reachable',len(seen),'viaSites',len(exits),'nearest',min(exits,key=lambda e:math.dist(e,(p['x'],p['y']))) if exits else None,flush=True)
