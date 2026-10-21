from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text().replace('pcb-pads-power-v07.json','pcb-pads-usb-v07.json').replace('routing-power-v07.json','routing-ground-resume-v07.json'))
from shapely import affinity
tracks=[t for t in tracks if t['net']!='LTE_BOOT_SOURCE' and not (t['net']=='LTE_USB_DM_EXT' and t['geom'].distance(Point(41.099,64.5495))<.001)]
c=next(c for c in cs if c['ref']=='D21');errs=[]
for p in pads:
 if p['ref']!='D21':continue
 g=affinity.translate(affinity.rotate(p['geom'],180,origin=(c['x']*.0254,c['y']*.0254)),xoff=41.099-c['x']*.0254,yoff=64.9-c['y']*.0254)
 for q in pads:
  if q['ref']!='D21' and g.buffer(.153).intersects(q['geom']):errs.append(('pad',q['ref'],q['net']))
 for t in tracks:
  if t['layer']==1 and t['net']!=p['net'] and g.buffer(.153).intersects(t['geom']):errs.append(('track',t['net']))
 for v in vias:
  if v['net']!=p['net'] and g.buffer(.153).intersects(Point(v['x'],v['y']).buffer(v['diameter']/2)):errs.append(('via',v['net']))
print('D21 adjusted placement collisions',errs)
r=json.loads((P/'manifests/routing-ground-resume-v07.json').read_text(encoding='utf-8-sig'))['result'];target=[]
for q in r['polys']:
 if q['net']=='LTE_USB_DM_EXT' and abs(q['polygon'][0]*.0254-41.099)<.003 and abs(q['polygon'][1]*.0254-64.5495)<.003:target.append(q['id'])
print('ESD branch to update',target)
if not errs and len(target)==1:
 bootpolys=[q['id'] for q in r['polys'] if q['net']=='LTE_BOOT_SOURCE'];bootvias=[q['id'] for q in r['vias'] if q['net']=='LTE_BOOT_SOURCE']
 code='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");if(!await eda.pcb_PrimitivePolyline.delete('+json.dumps(target)+'))throw Error("Delete failed");if('+json.dumps(bootpolys)+'.length)await eda.pcb_PrimitivePolyline.delete('+json.dumps(bootpolys)+');if('+json.dumps(bootvias)+'.length)await eda.pcb_PrimitiveVia.delete('+json.dumps(bootvias)+');const c=(await eda.pcb_PrimitiveComponent.getAll()).find(c=>c.getState_Designator()==="D21");await eda.pcb_PrimitiveComponent.modify(c,{x:41.099/.0254,y:64.9/.0254,rotation:270});return {saved:await eda.pcb_Document.save()};';(P/'scripts/adjust-d21-v07.js').write_text(code)



