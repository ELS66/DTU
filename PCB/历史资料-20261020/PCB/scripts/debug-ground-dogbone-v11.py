from pathlib import Path
s=Path('PCB/scripts/plan-interface-routing-v11.py').read_text();exec(s[:s.rindex('d=json.loads')]);net='GND';obs=unary_union([obstacles(net,k) for k in [1,2,16]]);own=unary_union([p['geom'] for p in pads if p['net']==net and p['layer']==1]);top=obstacles(net,1)
for ref,num in [('U7','8'),('U7','15'),('U7','10'),('C34','2'),('C33','2')]:
 p=next(p for p in pads if p['ref']==ref and p['number']==num);a=(p['x'],p['y']);c=[]
 for x in np.arange(a[0]-2,a[0]+2,.1):
  for y in np.arange(a[1]-2,a[1]+2,.1):
   q=Point(x,y)
   if q.distance(obs)>.225+.154 and q.distance(own)>.15 and LineString([a,(x,y)]).distance(top)>.0762+.154:c.append((math.dist(a,(x,y)),x,y))
 print(ref,num,min(c) if c else 'NONE',flush=True)
