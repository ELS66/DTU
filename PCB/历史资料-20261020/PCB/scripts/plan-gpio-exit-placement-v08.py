from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text().replace('pcb-pads-power-v07.json','pcb-pads-rs232-v08.json').replace('routing-power-v07.json','routing-reference-v08.json'))
from shapely import affinity
specs=json.loads((P/'manifests/gpio-exit-placement-v08.json').read_text());refs={s['ref'] for s in specs};newpads=[];coll=[]
for z in specs:
 ref,x,y,rot=z['ref'],z['x'],z['y'],z['rotation'];c=next(c for c in cs if c['ref']==ref);cen=c['x']*.0254,c['y']*.0254
 for p in pads:
  if p['ref']!=ref:continue
  g=affinity.translate(affinity.rotate(p['geom'],rot-c['rotation'],origin=cen),xoff=x-cen[0],yoff=y-cen[1]);newpads.append({**p,'geom':g,'x':g.centroid.x,'y':g.centroid.y})
for i,p in enumerate(newpads):
 for q in [r for r in pads if r['ref'] not in refs]+newpads[:i]:
  if p['ref']!=q['ref'] and p['geom'].buffer(.153).intersects(q['geom']):coll.append((p['ref'],p['number'],q['ref'],q['number']))
print('pad placement collisions',coll)
delnets=set();polys=[];vdel=[]
for q in old['polys']:
 if q['layer'] not in [1,2,15,16]:continue
 a=q['polygon'];v=[x for x in a[3:] if isinstance(x,(int,float))];xy=[(a[0]*.0254,a[1]*.0254)]+list(zip([x*.0254 for x in v[::2]],[x*.0254 for x in v[1::2]]));g=LineString(xy).buffer(q['width']*.0254/2)
 touchold=any(p['ref'] in refs and p['net']==q['net'] and (p['geom'].buffer(.03).covers(Point(*xy[0])) or p['geom'].buffer(.03).covers(Point(*xy[-1]))) for p in pads) if q['layer']==1 else False
 hitnew=any(p['net']!=q['net'] and p['geom'].buffer(.153).intersects(g) for p in newpads) if q['layer']==1 else False
 if q['net'] in delnets or touchold or hitnew:polys.append(q['id'])
for v in old['vias']:
 g=Point(v['x']*.0254,v['y']*.0254).buffer(v['diameter']*.0254/2)
 if v['net'] in delnets or any(p['net']!=v['net'] and p['geom'].buffer(.153).intersects(g) for p in newpads):vdel.append(v['id'])
print('targeted cleanup',len(polys),'polys',len(vdel),'vias');print('affected nets',sorted({q['net'] for q in old['polys'] if q['id'] in polys}))
plan={'placements':specs,'deletePolys':polys,'deleteVias':vdel,'padCollisions':coll};(P/'manifests/gpio-exit-plan-v08.json').write_text(json.dumps(plan,indent=2))
if not coll:
 guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");'
 code=guard+'const plan='+json.dumps(plan)+';if(plan.deletePolys.length&&!await eda.pcb_PrimitivePolyline.delete(plan.deletePolys))throw Error("Delete traces failed");if(plan.deleteVias.length&&!await eda.pcb_PrimitiveVia.delete(plan.deleteVias))throw Error("Delete vias failed");const all=await eda.pcb_PrimitiveComponent.getAll();for(const z of plan.placements){const c=all.find(c=>c.getState_Designator()===z.ref);if(!await eda.pcb_PrimitiveComponent.modify(c,{x:z.x/.0254,y:z.y/.0254,rotation:z.rotation}))throw Error("Move failed "+z.ref);}return {moved:plan.placements.length,saved:await eda.pcb_Document.save()};'
 (P/'scripts/apply-gpio-exit-placement-v08.js').write_text(code)
