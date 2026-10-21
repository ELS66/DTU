from pathlib import Path
s=Path('PCB/scripts/plan-interface-routing-v11.py').read_text();exec(s[:s.rindex('d=json.loads')]);net='232_VPLUS';p=next(p for p in pads if p['ref']=='U7' and p['number']=='2');print('pin',p['geom'].bounds)
for x,y in [(28.65,13.65),(28.65,13.7),(28.65,13.75),(28.65,13.8)]:
 print(x,y,'obs',[(k,round(Point(x,y).distance(obstacles(net,k)),4)) for k in [1,2,16]],'own',round(Point(x,y).distance(unary_union([p['geom'] for p in pads if p['net']==net and p['layer']==1])),4))
pt=Point(28.75,15.95);print('closest top',sorted([(round(pt.distance(p['geom']),3),'pad',p['ref'],p['number'],p['net']) for p in pads if p['net']!=net and p['layer']==1]+[(round(pt.distance(t['geom']),3),'track',t['net'],'','') for t in tracks if t['net']!=net and t['layer']==1])[:7])

pt=Point(28.65,13.7);print('closest under',sorted([(round(pt.distance(t['geom']),3),t['layer'],t['net']) for t in tracks if t['net']!='232_VPLUS' and t['layer'] in [1,2,16]])[:8])
