from pathlib import Path
s=Path('PCB/scripts/plan-interface-routing-v11.py').read_text();exec(s[:s.rindex('d=json.loads')]);net='232_TOUT'
for x,y in [(27.95,10.3),(27.95,10.4),(28,10.5),(28,8.0),(28,7.8)]:
 pt=Point(x,y);print(x,y,'obs',[(k,round(pt.distance(obstacles(net,k)),3)) for k in [1,2,16]],'closest',sorted([(round(pt.distance(t['geom']),3),t['net']) for t in tracks if t['net']!=net and t['layer']==1])[:2])
