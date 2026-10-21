from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text().replace('routing-power-v07.json','routing-interface-v11.json').replace('pcb-pads-power-v07.json','pcb-pads-interface-v11.json'))
holes=[Point(h['x'],h['y']).buffer(h['radius'],quad_segs=24) for h in json.loads((P/'manifests/mechanical-holes-v07.json').read_text())]
obs=[Point(v['x'],v['y']).buffer((v['diameter']/2+.28)/math.cos(math.pi/32),quad_segs=8) for v in vias if v['net']!='GND']+[p['geom'].buffer(.28,quad_segs=8) for p in pads if p['layer']==12 and p['net']!='GND']+[h.buffer(.3,quad_segs=8) for h in holes]
plane=box(.4,.4,59.6,69.6).difference(unary_union(obs));parts=list(plane.geoms) if hasattr(plane,'geoms') else [plane];parts=[g for g in parts if any(g.intersects(Point(v['x'],v['y']).buffer(.225)) for v in vias if v['net']=='GND')];plane=unary_union(parts);out=[]
for i in range(75):
 strip=box(.4+i*.8,.4,min(59.6,.4+(i+1)*.8+.002),69.6).intersection(plane)
 for g in list(strip.geoms) if hasattr(strip,'geoms') else [strip]:
  if g.geom_type!='Polygon' or g.area<.0001:continue
  if len(g.interiors):raise Exception('Interior hole in slab')
  pts=[[round(x/.0254,4),round(y/.0254,4)] for x,y in g.exterior.coords];out.append([*pts[0],'L',*[t for q in pts[1:] for t in q]])
(P/'manifests/ground-fill-plan-v11.json').write_text(json.dumps({'layer':15,'net':'GND','areaMm2':plane.area,'polygons':out},indent=2));guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");'
(P/'scripts/clear-ground-fill-v11.js').write_text(guard+'const ids=await eda.pcb_PrimitiveFill.getAllPrimitiveId(15,"GND");if(ids.length&&!await eda.pcb_PrimitiveFill.delete(ids))throw Error("Plane deletion failed");return {removed:ids.length,saved:await eda.pcb_Document.save()};')
for i in range(0,len(out),20):
 code=guard+'const ps='+json.dumps(out[i:i+20])+';const ids=[];for(const a of ps){const p=await eda.pcb_PrimitiveFill.create(15,eda.pcb_MathPolygon.createPolygon(a),"GND",0,undefined,false);if(!p)throw Error("Fill failed");ids.push(p.getState_PrimitiveId());}return {ids,saved:await eda.pcb_Document.save()};';(P/f'scripts/apply-ground-fill-v11-{i//20+1}.js').write_text(code)
print('Plane area',plane.area,'polygons',len(out),'batches',math.ceil(len(out)/20))
