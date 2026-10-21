from pathlib import Path
s=Path('PCB/scripts/plan-interface-routing-v11.py').read_text();exec(s[:s.rindex('d=json.loads')]);remove=['FIELD_TX','232_TOUT','232_RIN','232_RX_RAW','485_RX_RAW'];tracks[:]=[t for t in tracks if t['net'] not in remove];vias[:]=[v for v in vias if v['net'] not in remove]
for num in ['11','12','13','14']:
 p=next(p for p in pads if p['ref']=='U7' and p['number']==num);net=p['net'];a=(p['x'],p['y']);obs=unary_union([obstacles(net,k) for k in [1,2,16]]);own=unary_union([p['geom'] for p in pads if p['net']==net and p['layer']==1]);top=obstacles(net,1);c=[]
 for x in np.arange(a[0]-2,a[0]+2.01,.1):
  for y in np.arange(10.3,13.51,.05):
   q=Point(x,y)
   if q.distance(obs)>.225+.154 and q.distance(own)>.15 and LineString([a,(x,y)]).distance(top)>.0762+.154:c.append((math.dist(a,(x,y)),float(x),float(y)))
 v=min(c) if c else None;print(num,net,v,flush=True)
 if v: vias.append({'net':net,'x':v[1],'y':v[2],'diameter':.45})
pt=Point(26.675,10.6);print('rx closest',sorted([(round(pt.distance(t['geom']),3),t['layer'],t['net']) for t in tracks if t['net']!='232_RX_RAW' and t['layer'] in [1,2,16]])[:8]);print('pads',sorted([(round(pt.distance(p['geom']),3),p['ref'],p['number'],p['net']) for p in pads if p['net']!='232_RX_RAW' and p['layer'] in [1,12]])[:4])


line=LineString([(27.32532,9.13384),(27.32532,11.3)]);print('RIN neck',sorted([(round(line.distance(t['geom']),3),t['layer'],t['net']) for t in tracks if t['net']!='232_RIN' and t['layer']==1])[:6])
