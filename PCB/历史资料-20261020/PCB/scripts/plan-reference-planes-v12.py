from pathlib import Path
exec(Path('PCB/scripts/router-v12.py').read_text(encoding='utf8'))
for name in ['rf-routing-v12','usb-routing-retained-v12','usb-rework-v12','supply-ground-fanout-v12','supply-ground-repair-v12']:load_plan(P/f'manifests/{name}.json')
planes=[]
for layer,boundary in [(15,box(.4,.4,49.6,59.6)),(16,box(14.5,40.8,20.8,49.2))]:
 obs=[Point(v['x'],v['y']).buffer(v['diameter']/2+.2,quad_segs=12) for v in vias if v['net']!='GND']+[p['geom'].buffer(.2) for p in pads if p['layer']==12 and p['net']!='GND']+holes
 if layer==16:obs += [t['geom'].buffer(.2) for t in tracks if t['layer']==16 and t['net']!='GND']
 plane=boundary.difference(unary_union(obs));gs=list(plane.geoms) if hasattr(plane,'geoms') else [plane];gs=[g for g in gs if any(g.intersects(Point(v['x'],v['y']).buffer(v['diameter']/2)) for v in vias if v['net']=='GND')];plane=unary_union(gs)
 for x in np.arange(.4,49.6,.5):
  g=plane.intersection(box(x,.4,x+.502,59.6))
  for q in list(g.geoms) if hasattr(g,'geoms') else [g]:
   if q.geom_type!='Polygon' or q.area<1e-5:continue
   if q.interiors:raise Exception('Slab hole')
   pts=[v/.0254 for xy in q.exterior.coords for v in xy];planes.append({'layer':layer,'poly':[pts[0],pts[1],'L',*pts[2:]]})
 print('Plane',layer,plane.area,flush=True)
(P/'manifests/reference-planes-v12.json').write_text(json.dumps(planes,indent=2))
guard=(P/'scripts/read-pcb-pads-v12.js').read_text().split('const out=')[0]
for i in range(0,len(planes),20):
 code=guard+'const regions='+json.dumps(planes[i:i+20])+";const ids=[];for(const r of regions){const p=await eda.pcb_PrimitiveFill.create(r.layer,eda.pcb_MathPolygon.createPolygon(r.poly),'GND',0,undefined,false);if(!p)throw Error('Plane failed');ids.push(p.getState_PrimitiveId());}return {ids,saved:await eda.pcb_Document.save()};"
 (P/f'scripts/apply-reference-planes-v12-{i//20+1}.js').write_text(code,encoding='utf8')
