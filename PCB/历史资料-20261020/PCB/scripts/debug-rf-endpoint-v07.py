from pathlib import Path
s=Path('PCB/scripts/plan-rf-routing-v07.py').read_text();s=s[:s.index('routes=[]')];exec(s)
a=xy('U2','35');b=xy('R50','1');geom=obstacles('LTE_ANT',1)
print('endpoints',a,b,'foreign distances',Point(*a).distance(geom),Point(*b).distance(geom))
for p in pads:
 if p['net']!='LTE_ANT' and p['geom'].distance(Point(*a))<.5:print('nearby pad',p['ref'],p['number'],p['net'],p['geom'].bounds)
for t in tracks:
 if t['net']!='LTE_ANT' and t['layer']==1 and t['geom'].distance(Point(*a))<.5:print('nearby track',t['net'],t['geom'].bounds)
for v in vias:
 if v['net']!='LTE_ANT' and math.dist(a,(v['x'],v['y']))<1:print('via',v)
