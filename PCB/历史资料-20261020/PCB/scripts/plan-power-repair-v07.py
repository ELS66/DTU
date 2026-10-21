from pathlib import Path
exec(Path('PCB/scripts/repair-routing-core-v07.py').read_text(encoding='utf-8'))
from shapely.ops import nearest_points
plan=json.loads((P/'manifests/power-routing-v07.json').read_text());targets=[x for x in plan['failed'] if 'from' in x]
for z in targets:
 net=z['net'];a=z['from'];b=z['to'];mask,obs=raster(net,1,.2032);pts=astar(a,b,mask)
 if pts:add(net,1,pts,.2032)
 else:fails.append(z)
 print('bridge',net,bool(pts),flush=True)
for z in [x for x in plan['failed'] if 'pad' in x]:
 q=next(q for q in pads if q['ref']+':'+q['number']==z['pad']);net=q['net'];a=(q['x'],q['y']);others=[p for p in pads if p['net']==net and p['ref']+':'+p['number']!=z['pad']];ts=[(v['x'],v['y']) for v in vias if v['net']==net]+[tuple(nearest_points(Point(*a),p['geom'])[1].coords[0]) for p in others];ts=sorted(ts,key=lambda b:math.dist(a,b));mask,obs=raster(net,1,.1524);done=False
 for b in ts[:50]:
  if math.dist(a,b)<.01:continue
  pts=astar(a,b,mask)
  if pts:add(net,1,pts,.1524);done=True;break
 if not done:fails.append(z)
 print('fanout repair',z['pad'],done,flush=True)
# Add a separate wide 3.3V feed between the regulator output and MCU.
net='VDD_3V3';src=next(p for p in pads if p['ref']=='L2' and p['number']=='2');dst=next(p for p in pads if p['ref']=='U1' and p['number']=='2');sinks=lambda q:[tuple(r['pointsMm'][-1]) for r in f['routes'] if r['net']==net and math.dist(r['pointsMm'][0],(q['x'],q['y']))<.001]
sources=sinks(src);destinations=sinks(dst);mask,obs=raster(net,2,.8);done=False
for a in sources:
 for b in destinations:
  pts=astar(a,b,mask)
  if pts:add(net,2,pts,.8);done=True;break
 if done:break
print('wide MCU feed',done,flush=True)
if not done:fails.append({'net':net,'stage':'wide MCU feed'})
plan={'routes':new,'failed':fails};(P/'manifests/power-repair-v07.json').write_text(json.dumps(plan,indent=2));print('repair summary',len(new),'failed',fails,flush=True)
guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");'
code=guard+'const specs='+json.dumps(new)+';for(const z of specs){const p=z.pointsMm;const a=[p[0][0]/.0254,p[0][1]/.0254,"L",...p.slice(1).flatMap(q=>q.map(v=>v/.0254))];if(!await eda.pcb_PrimitivePolyline.create(z.net,z.layer,eda.pcb_MathPolygon.createPolygon(a),z.widthMm/.0254,false))throw Error("Repair failed");}return {created:specs.length,saved:await eda.pcb_Document.save()};';(P/'scripts/apply-power-repair-v07.js').write_text(code)
