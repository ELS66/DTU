from pathlib import Path
exec(Path('PCB/scripts/router-v12.py').read_text())
for name in ['rf-routing-v12','usb-routing-retained-v12','usb-rework-v12','supply-ground-fanout-v12','supply-ground-repair-v12']:load_plan(P/f'manifests/{name}.json')
native=json.load(open(P/'manifests/routing-fanout-v12.json'))['result'];c=by['C54'];old=(c['x']*.0254,c['y']*.0254);foreign=unary_union([p['geom'] for p in pads if p['ref']!='C54' and p['layer']==2]+[t['geom'] for t in tracks if t['layer']==2]+holes);g=unary_union([p['geom'] for p in pads if p['ref']=='C54']).buffer(.2);opts=[]
for x in np.arange(5,45,.25):
 for y in np.arange(8,52,.25):
  q=translate(g,x-old[0],y-old[1])
  if not q.intersects(foreign):opts.append((math.dist((x,y),old),round(x,3),round(y,3)))
_,x,y=min(opts);print('C54 move',x,y)
# Delete the old C54 ground spoke. The existing ground via remains tied to the plane.
padold=xy('C54','2');remove=[]
for r in native['polys']:
 if r['net']=='GND' and any(math.dist((r['polygon'][i]*.0254,r['polygon'][i+1]*.0254),padold)<.02 for i in [0]):remove.append(r['id'])
slotbad=[v for v in native['vias'] if v['net']=='VDD_3V3' and any(Point(v['x']*.0254,v['y']*.0254).distance(h)<v['diameter']*.0254/2+.153 for h in holes[-2:])]
print('Bad via',slotbad)
for v in slotbad:
 for r in native['polys']:
  if r['net']==v['net'] and any(math.dist((r['polygon'][i],r['polygon'][i+1]),(v['x'],v['y']))<.1 for i in [0,len(r['polygon'])-2]):remove.append(r['id'])
guard=(P/'scripts/read-pcb-pads-v12.js').read_text().split('const out=')[0]
code=guard+'const ps='+json.dumps(remove)+';if(ps.length&&!await eda.pcb_PrimitivePolyline.delete(ps))throw Error("Spoke delete failed");const vs='+json.dumps([v['id'] for v in slotbad])+';if(vs.length&&!await eda.pcb_PrimitiveVia.delete(vs))throw Error("Via delete failed");const c=(await eda.pcb_PrimitiveComponent.getAll()).find(c=>c.getState_Designator()==="C54");c.toAsync();c.setState_X('+str(x/.0254)+');c.setState_Y('+str(y/.0254)+');if(!await c.done())throw Error("Move failed");return {saved:await eda.pcb_Document.save()};'
(P/'scripts/fix-sim-clearance-v12.js').write_text(code,encoding='utf8')
(P/'manifests/sim-clearance-rework-v12.json').write_text(json.dumps({'C54':[x,y],'removedPolys':remove,'removedVias':slotbad},indent=2))

