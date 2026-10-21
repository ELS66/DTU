from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text().replace('routing-power-v07.json','routing-interface-v11.json').replace('pcb-pads-power-v07.json','pcb-pads-interface-v11.json'))
fills=json.loads((P/'manifests/inner2-fills-v11.json').read_text(encoding='utf-8-sig'))['result']
drc=json.loads((P/'reports/pcb-drc-interface-v11.json').read_text(encoding='utf-8-sig'))['result']
ids={z['explanation']['errData'][k] for g in drc for t in g['list'] for z in t['list'] for k in ['obj1','obj2'] if z['explanation']['errData'][k+'Type']=='Fill Region'}
obs=unary_union([t['geom'].buffer(.28) for t in tracks if t['layer']==16 and t['net']!='GND']+[Point(v['x'],v['y']).buffer((v['diameter']/2+.28)/math.cos(math.pi/32),quad_segs=8) for v in vias if v['net']!='GND'])
changed=[]
for f in fills:
 if f['id'] not in ids:continue
 a=f['polygon'];v=[x for x in a[3:] if isinstance(x,(int,float))];pts=[(a[0]*.0254,a[1]*.0254)]+list(zip([x*.0254 for x in v[::2]],[x*.0254 for x in v[1::2]]));before=Polygon(pts);after=before.difference(obs);new=[]
 for g in list(after.geoms) if hasattr(after,'geoms') else [after]:
  if g.geom_type!='Polygon' or g.area<.0001:continue
  if g.interiors:raise Exception('Unexpected interior hole')
  pts=[[round(x/.0254,4),round(y/.0254,4)] for x,y in g.exterior.coords];new.append([*pts[0],'L',*[t for q in pts[1:] for t in q]])
 changed.append({'id':f['id'],'beforeArea':before.area,'afterArea':after.area,'polygons':new})
(P/'manifests/inner2-fill-repair-v11.json').write_text(json.dumps(changed,indent=2))
code='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");const plan='+json.dumps(changed)+';const ids=[];for(const f of plan){for(const a of f.polygons){const p=await eda.pcb_PrimitiveFill.create(16,eda.pcb_MathPolygon.createPolygon(a),"GND",0,undefined,false);if(!p)throw Error("Fill failed");ids.push(p.getState_PrimitiveId());}if(!await eda.pcb_PrimitiveFill.delete(f.id))throw Error("Deletion failed");}return {replaced:plan.length,ids,saved:await eda.pcb_Document.save()};'
(P/'scripts/apply-inner2-fill-repair-v11.js').write_text(code)
print('Repair fills',len(changed),'removed area',sum(f['beforeArea']-f['afterArea'] for f in changed))
