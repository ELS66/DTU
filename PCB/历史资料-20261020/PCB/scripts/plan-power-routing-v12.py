from pathlib import Path
exec(Path('PCB/scripts/router-v12.py').read_text(encoding='utf8'))
for name in ['rf-routing-v12','usb-routing-retained-v12','usb-rework-v12','supply-ground-fanout-v12','supply-ground-repair-v12']:load_plan(P/f'manifests/{name}.json')
base_obstacles=obstacles
def obstacles(net,layer,ignore=()):
 g=base_obstacles(net,layer,ignore)
 if layer==16 and net!='GND':g=unary_union([g,box(14.5,40.8,20.8,49.2)])
 return g
fails=[]
for net in ['LTE_SW','MCU_SW','TTL_BOOST_SW','LTE_BST','MCU_BST','LTE_FB','TTL_5V_FB','LTE_PWR_EN']:
 ps=[(p['x'],p['y'],p['layer']) for p in pads if p['net']==net];conn=[ps[0]];rest=ps[1:]
 while rest:
  _,i,j=min((math.dist(a[:2],b[:2]),i,j) for i,a in enumerate(conn) for j,b in enumerate(rest));a=conn[i];b=rest.pop(j)
  widths=[.6,.45,.254] if net.endswith('_SW') else [.2032,.1524]
  for w in widths:
   if addroute(net,a,b,w,(1,2)):break
  else:fails.append({'net':net,'from':a,'to':b})
  conn.append(b)
 print('Local',net,'fails',len(fails),flush=True)
for net in ['VIN_485','VIN_232','VIN_TTL','VIN_485_FUSED','VIN_232_FUSED','VIN_TTL_FUSED','VIN_OR','VIN_PROT','VDD_4G','VDD_3V3','VDD_5V_IF','LTE_VDD_EXT','SIM_VDD']:
 ps=[(v['x'],v['y'],16) for v in vias if v['net']==net]+[(p['x'],p['y'],16) for p in pads if p['net']==net and p['layer']==12];ps=list(dict.fromkeys(ps));conn=ps[:1];rest=ps[1:]
 while rest:
  _,i,j=min((math.dist(a[:2],b[:2]),i,j) for i,a in enumerate(conn) for j,b in enumerate(rest));a=conn[i];b=rest.pop(j);begin=len(new)
  for w in [.35,.254]:
   if addroute(net,a,b,w,(16,)):break
  else:fails.append({'net':net,'from':a,'to':b});conn.append(b);continue
  # Increase each segment independently wherever clearance permits.
  rs=new[begin:];del new[begin:];del tracks[len(tracks)-len(rs):]
  maximum=1.5 if net=='VDD_4G' or net.startswith('VIN') else .8 if net in ['VDD_3V3','VDD_5V_IF'] else .35
  for r in rs:
   obs=obstacles(net,r['layer'])
   for aa,bb in zip(r['pointsMm'],r['pointsMm'][1:]):
    line=LineString([aa,bb]);width=min(maximum,2*(line.distance(obs)-.158));width=max(w,math.floor(width/.025)*.025)
    assert addline(net,r['layer'],[aa,bb],width)
  conn.append(b)
 print('Power',net,'routes',len(new),'fails',len(fails),flush=True)
save_plan('power-routing-v12',fails)
