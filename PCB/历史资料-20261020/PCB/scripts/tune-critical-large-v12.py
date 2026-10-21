from pathlib import Path
exec(Path('PCB/scripts/check-usb-lengths-large-v12.py').read_text(encoding='utf8').split('for fam,refs,j in')[0])
original=json.loads(json.dumps(plan));remove={22,27,32}
for i,r in enumerate(plan['routes']):
 if i not in remove:tracks.append({'net':r['net'],'layer':r['layer'],'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2)})
vias.extend(plan['vias']);load_plan(P/'manifests/supply-ground-fanout-large-v12.json')
mods={27:[[21.83892,56.95442],[21.75,57.04334],[21.75,59.65],[20.9,60.5],[18.0,60.5]]}
def valid(i,pts):
 r=plan['routes'][i];return LineString(pts).distance(obstacles(r['net'],r['layer']))>=r['widthMm']/2+.153
for i,pts in mods.items():
 if not valid(i,pts):
  g=LineString(pts);print('Pad clashes',[(p['ref'],p['number'],g.distance(p['geom'])) for p in pads if p['layer']==2 and p['net']!=plan['routes'][i]['net'] and g.distance(p['geom'])<.273]);print('Via clashes',[(v['net'],v['x'],v['y'],g.distance(Point(v['x'],v['y']))-v['diameter']/2) for v in vias if v['net']!=plan['routes'][i]['net'] and g.distance(Point(v['x'],v['y']))-v['diameter']/2<.273]);print('Trace clashes',[(t['net'],g.distance(t['geom'])) for t in tracks if t['layer']==2 and t['net']!=plan['routes'][i]['net'] and g.distance(t['geom'])<.273])
  raise Exception('Critical replacement collides '+str(i))
 plan['routes'][i]['pointsMm']=pts;tracks.append({'net':plan['routes'][i]['net'],'layer':plan['routes'][i]['layer'],'geom':LineString(pts).buffer(plan['routes'][i]['widthMm']/2)})
def total(fam,side,res,pn):return length(f'{fam}_USB_{side}_EXT',res,'2','J6' if fam=='ESP' else 'J7')+length(f'{fam}_USB_{side}','U1' if fam=='ESP' else 'U2',pn,res,'1')
target=total('ESP','DP','R15','14');opts=[];constant=total('ESP','DM','R16','13')-LineString(original['routes'][22]['pointsMm']).length;obs=obstacles('ESP_USB_DM_EXT',2)
for y in np.arange(41.7,43.0,.005):
 pts=[[30.7467,41.26992],[30.7467,float(y)],[29.3,float(y)],[29.3,41.5]]
 if LineString(pts).distance(obs)>=.273:
  opts.append((abs(constant+LineString(pts).length-target),pts))
err,pts=min(opts);mods[22]=pts;plan['routes'][22]['pointsMm']=pts;print('ESP matched skew',err,flush=True)
target=total('LTE','DP','R60','59');opts=[];constant=total('LTE','DM','R61','60')-LineString(original['routes'][32]['pointsMm']).length;obs=obstacles('LTE_USB_DM_EXT',2)
# A compact rectangular detour crosses underneath the pair's top-side fanout.
for x in np.arange(18.7,20.2,.01):
 for y in np.arange(57.3,58.1,.05):
  pts=[[20.64004,56.95442],[20.64004,float(y)],[float(x),float(y)],[float(x),59.6],[20.65,59.35]]
  if LineString(pts).distance(obs)>=.273:
   opts.append((abs(constant+LineString(pts).length-target),pts))
err,pts=min(opts);mods[32]=pts;plan['routes'][32]['pointsMm']=pts;print('LTE matched skew',err,flush=True)
if err>.15:raise Exception('USB match exceeds target')
(P/'manifests/critical-large-before-tuning-v12.json').write_text(json.dumps(original,indent=2),encoding='utf8')
(P/'manifests/critical-large-v12.json').write_text(json.dumps(plan,indent=2),encoding='utf8')
ids=[]
for n in [1,2]:ids.extend(json.load(open(P/f'manifests/apply-critical-large-v12-{n}-result.json'))['result']['ids'])
items=[]
for i,pts in mods.items():items.append({'id':ids[len(original['vias'])+i],'net':plan['routes'][i]['net'],'poly':[pts[0][0]/.0254,pts[0][1]/.0254,'L',*[v/.0254 for p in pts[1:] for v in p]]})
guard=(P/'scripts/read-pcb-pads-v12.js').read_text().split('const out=')[0]
code=guard+'const items='+json.dumps(items)+";for(const i of items){const p=await eda.pcb_PrimitivePolyline.get(i.id);if(!p||p.getState_Net()!==i.net)throw Error('Wrong critical primitive');const a=p.toAsync();a.setState_Polygon(eda.pcb_MathPolygon.createPolygon(i.poly));await a.done();}return {modified:items.map(i=>i.id),saved:await eda.pcb_Document.save()};"
(P/'scripts/apply-critical-tuning-large-v12.js').write_text(code,encoding='utf8')
