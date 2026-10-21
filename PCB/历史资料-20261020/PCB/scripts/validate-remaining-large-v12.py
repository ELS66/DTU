from pathlib import Path
exec(Path('PCB/scripts/load-native-routing-large-v12.py').read_text(encoding='utf8').replace('routing-power-large-v12.json','routing-before-remaining-large-v12.json'))
a=json.load(open(P/'manifests/remaining-routing-large-v12.json'));bad=set();reasons=[]
for v in a['vias']:
 obs=unary_union([base_obstacles(v['net'],k) for k in layers]);gap=Point(v['x'],v['y']).distance(obs)-v['diameter']/2
 if gap<.1524:bad.add(v['net']);reasons.append([v['net'],'via',gap,v['x'],v['y']])
for r in a['routes']:
 gap=LineString(r['pointsMm']).distance(base_obstacles(r['net'],r['layer']))-r['widthMm']/2
 if gap<.1524:bad.add(r['net']);reasons.append([r['net'],'route',gap])
new.extend(r for r in a['routes'] if r['net'] not in bad);newvias.extend(v for v in a['vias'] if v['net'] not in bad)
save_plan('remaining-validated-large-v12',a['failed']+[{'net':n,'reason':'replan after USB tuning'} for n in sorted(bad)]);print('rejected',reasons)
