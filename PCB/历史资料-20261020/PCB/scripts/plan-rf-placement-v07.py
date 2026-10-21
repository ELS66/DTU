from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text().replace('routing-power-v07.json','routing-fixed-signals-v07.json'))
from shapely import affinity
by={c['ref']:c for c in cs};moving={'C50','C51','D10'};occupied=[p for p in pads if p['ref'] not in moving];fixedtracks=[t for t in tracks if t['layer']==1 and t['net'] not in ['GND','LTE_ANT','LTE_RF_FEED']];mov={};placed=[]
for ref,target in [('D10',(53.553,49.2)),('C50',(52.045,49.2)),('C51',(53.553,49.2))]:
 c=by[ref];original=[p for p in pads if p['ref']==ref];cx,cy=c['x']*.0254,c['y']*.0254;opts=[];obsby={p['net']:unary_union([t['geom'] for t in fixedtracks if t['net']!=p['net']]+[Point(v['x'],v['y']).buffer(v['diameter']/2) for v in vias if v['net']!=p['net']]) for p in original};padobs=unary_union([p['geom'] for p in occupied+placed])
 for ix in range(255,295):
  for iy in range(243,265):
   x,y=ix*.2,iy*.2
   for rot in [0,90,180,270]:
    shapes=[affinity.translate(affinity.rotate(p['geom'],rot-c['rotation'],origin=(cx,cy)),xoff=x-cx,yoff=y-cy) for p in original];body=unary_union(shapes).envelope.buffer(.10)
    if body.buffer(.15).intersects(padobs):continue
    good=True
    for p,g in zip(original,shapes):
     obs=obsby[p['net']]
     if g.buffer(.16).intersects(obs):good=False;break
    if not good:continue
    rf=next(g.centroid for p,g in zip(original,shapes) if p['net']!='GND');opts.append((math.dist((rf.x,rf.y),target),x,y,rot,shapes))
 if not opts:raise Exception('No RF placement '+ref)
 _,x,y,rot,shapes=min(opts,key=lambda z:z[0]);mov[ref]=[x,y,rot];placed.extend([{'geom':g} for g in shapes]);print(ref,mov[ref],'RF stub',round(min(z[0] for z in opts),3))
(P/'manifests/rf-placement-v07.json').write_text(json.dumps(mov,indent=2));guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");'
code=guard+'const moves='+json.dumps([{'ref':r,'x':v[0]/.0254,'y':v[1]/.0254,'rotation':v[2]} for r,v in mov.items()])+';const cs=await eda.pcb_PrimitiveComponent.getAll();for(const q of moves){const c=cs.find(c=>c.getState_Designator()===q.ref);await eda.pcb_PrimitiveComponent.modify(c,{x:q.x,y:q.y,rotation:q.rotation});}const a=eda.pcb_MathPolygon.createPolygon([583.9,1848.3,"L",583.9,1781.4,517,1781.4]);if(!await eda.pcb_PrimitivePolyline.create("GND",1,a,.4/.0254,false))throw Error("Ground bridge failed");return {saved:await eda.pcb_Document.save()};';(P/'scripts/place-rf-v07.js').write_text(code)

