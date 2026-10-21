from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text().replace('routing-power-v07.json','routing-pre-port-v10.json').replace('pcb-pads-power-v07.json','pcb-pads-sim-v10.json'))
plan=json.loads((P/'manifests/port-main-plan-v10.json').read_text());errors=[]
ref=json.loads((P/'manifests/usb-ground-reference-plan-v09.json').read_text());rr=[]
for a in ref['polygons']:
 nums=[v for v in a if isinstance(v,(float,int))];rr.append(Polygon([(x*.0254,y*.0254) for x,y in zip(nums[::2],nums[1::2])]))
reference=unary_union(rr)
holes=unary_union([Point(h['x'],h['y']).buffer(h['radius']) for h in json.loads((P/'manifests/mechanical-holes-v07.json').read_text())])
for i,r in enumerate(plan['routes']):
 g=LineString(r['pointsMm']).buffer(r['widthMm']/2)
 obs=unary_union([obstacles(r['net'],r['layer']),holes.buffer(.3)]+([reference] if r['layer']==16 else []))
 if g.distance(obs)<.1524-1e-6:errors.append(f'Route {i} clearance')
 if not box(.3,.3,59.7,69.7).covers(g):errors.append(f'Route {i} board')
 tracks.append({'net':r['net'],'layer':r['layer'],'geom':g})
for i,v in enumerate(plan['vias']):
 g=Point(v['x'],v['y']).buffer(.3)
 obs=unary_union([obstacles(v['net'],l) for l in [1,2,16]]+[reference,holes.buffer(.3)])
 if g.distance(obs)<.1524-1e-6:errors.append(f'Via {i} clearance')
 if not box(.3,.3,59.7,69.7).covers(g):errors.append(f'Via {i} board')
 for w in vias:
  if math.dist((v['x'],v['y']),(w['x'],w['y']))<.62-1e-6:errors.append(f'Via {i} hole spacing')
 vias.append({**v,'diameter':.6})
result={'status':'PASS' if not errors else 'FAIL','routes':len(plan['routes']),'vias':len(plan['vias']),'errors':errors}
(P/'reports/port-plan-validation-v10.json').write_text(json.dumps(result,indent=2));print(result)
