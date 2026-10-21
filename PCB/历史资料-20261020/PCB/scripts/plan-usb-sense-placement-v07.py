from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text().replace('pcb-pads-power-v07.json','pcb-pads-usb-v07.json').replace('routing-power-v07.json','routing-usb-priority-v07.json'))
from shapely import affinity
tracks=[t for t in tracks if t['net'] not in ['TTL_VSENSE','RS485_VSENSE']];vias=[v for v in vias if v['net'] not in ['TTL_VSENSE','RS485_VSENSE']]
by={c['ref']:c for c in cs};targets={'C100':[37.4,27.4,90],'C102':[38.8,27.4,90]};moving=set(targets);occupied=unary_union([p['geom'] for p in pads if p['ref'] not in moving]);placed=[];mov={}
for ref,target in sorted(targets.items(),key=lambda v:v[0]=='R14'):
 c=by[ref];cx,cy=c['x']*.0254,c['y']*.0254;ps=[p for p in pads if p['ref']==ref];obsby={p['net']:unary_union([t['geom'] for t in tracks if t['layer']==1 and t['net']!=p['net']]+[Point(v['x'],v['y']).buffer(v['diameter']/2) for v in vias if v['net']!=p['net']]) for p in ps};bodyobs=unary_union([occupied]+placed);opts=[]
 for dx in [i*.1 for i in range(-20,21)]:
  for dy in [i*.1 for i in range(-20,21)]:
   x,y=target[0]+dx,target[1]+dy;rot=target[2];gs=[affinity.translate(affinity.rotate(p['geom'],rot-c['rotation'],origin=(cx,cy)),xoff=x-cx,yoff=y-cy) for p in ps];body=unary_union(gs).envelope.buffer(.07)
   if body.bounds[0]<.4 or body.bounds[2]>59.6 or body.buffer(.15).intersects(bodyobs):continue
   if any(g.buffer(.16).intersects(obsby[p['net']]) for p,g in zip(ps,gs)):continue
   opts.append((dx*dx+dy*dy,x,y,rot,body))
 if not opts:raise Exception('No USB placement '+ref)
 _,x,y,rot,body=min(opts,key=lambda z:z[0]);mov[ref]=[x,y,rot];placed.append(body);print(ref,mov[ref])
(P/'manifests/usb-sense-placement-v07.json').write_text(json.dumps(mov,indent=2));guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");';code=guard+'const ms='+json.dumps([{'ref':r,'x':v[0]/.0254,'y':v[1]/.0254,'rotation':v[2]} for r,v in mov.items()])+';const cs=await eda.pcb_PrimitiveComponent.getAll();for(const m of ms){const c=cs.find(c=>c.getState_Designator()===m.ref);await eda.pcb_PrimitiveComponent.modify(c,{x:m.x,y:m.y,rotation:m.rotation});}return {saved:await eda.pcb_Document.save()};';(P/'scripts/place-usb-sense-v07.js').write_text(code)

