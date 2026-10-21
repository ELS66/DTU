from pathlib import Path
s=Path('PCB/scripts/plan-interface-routing-v11.py').read_text();exec(s[:s.rindex('d=json.loads')]);from shapely import affinity
rp=[p for p in pads if p['ref']=='R30'];options=[];ob={p['net']:obstacles(p['net'],1) for p in rp}
for x in np.arange(8.8,11.51,.1):
 for y in np.arange(5.5,8.11,.1):
  geoms=[affinity.translate(affinity.rotate(p['geom'],-90,origin=(8.4,8)),x-8.4,y-8) for p in rp]
  if all(g.distance(ob[p['net']])>.16 for g,p in zip(geoms,rp)):options.append((math.dist((x,y),(9.8,6.8)),float(x),float(y)))
print('R30',min(options) if options else 'none')
pt=Point(23.9,51.745);print('LED obstacles',sorted([(round(pt.distance(t['geom']),3),t['net'],t['layer']) for t in tracks if t['layer']==1])[:6])

