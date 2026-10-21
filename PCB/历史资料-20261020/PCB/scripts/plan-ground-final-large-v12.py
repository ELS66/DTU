from pathlib import Path
exec(Path('PCB/scripts/load-native-routing-large-v12.py').read_text(encoding='utf-8-sig').replace('routing-power-large-v12.json','routing-signals-complete-large-v12.json'))
layers=[1,2,15,16]
# All copper including rare inner-1 repair traces, read from the actual PCB.
tracks=[]
for r in native['polys']:
 if not r['net'] or r['layer'] not in layers:continue
 a=r['polygon'];pts=[(a[0]*.0254,a[1]*.0254)]+[(a[i]*.0254,a[i+1]*.0254) for i in range(3,len(a),2)]
 tracks.append({'net':r['net'],'layer':r['layer'],'points':pts,'geom':LineString(pts).buffer(r['width']*.0254/2)})
allforeign=unary_union([p['geom'] for p in pads if p['net']!='GND']+[t['geom'] for t in tracks if t['net']!='GND']+[Point(v['x'],v['y']).buffer(v['diameter']/2) for v in vias if v['net']!='GND']+holes)
targets=[(x,y) for x in np.arange(6.5,15,1.3) for y in np.arange(57.3,65,1.3)]
usb=json.load(open(P/'manifests/critical-large-v12.json'))
for v in usb['vias']:
 if 'USB' in v['net']:targets.extend([(v['x']+dx,v['y']+dy) for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]])
for x,y in targets:
 pt=Point(x,y)
 if not(.8<x<59.2 and .8<y<69.2) or pt.distance(allforeign)<.225+.20:continue
 if any(math.dist((x,y),(v['x'],v['y']))<.75 for v in vias):continue
 v={'net':'GND','x':x,'y':y,'diameter':.45,'hole':.2};newvias.append(v);vias.append(v)
save_plan('ground-stitches-final-large-v12')
planes=[];areas={};actual=[]
for layer,boundary in [(15,box(.4,.4,59.6,69.6)),(16,box(.4,.4,59.6,69.6)),(1,box(6,56.8,15.5,65.3))]:
 obs=[Point(v['x'],v['y']).buffer(v['diameter']/2+.2,quad_segs=16) for v in vias if v['net']!='GND']+[p['geom'].buffer(.25 if layer==1 and p['net'] in ['LTE_ANT','LTE_RF_FEED'] else .2) for p in pads if p['layer'] in [layer,12] and p['net']!='GND']+holes
 obs += [t['geom'].buffer(.25 if layer==1 and t['net'] in ['LTE_ANT','LTE_RF_FEED'] else .2) for t in tracks if t['layer']==layer and t['net']!='GND']
 plane=boundary.difference(unary_union(obs));pieces=list(plane.geoms) if hasattr(plane,'geoms') else [plane]
 # No floating islands: each retained piece must contact an actual ground via or plated ground hole.
 contacts=[Point(v['x'],v['y']).buffer(v['diameter']/2) for v in vias if v['net']=='GND']+[p['geom'] for p in pads if p['net']=='GND' and p['layer'] in [layer,12]]
 pieces=[g for g in pieces if g.geom_type=='Polygon' and any(g.intersects(c) for c in contacts)];plane=unary_union(pieces);areas[layer]=plane.area
 actual.append({'layer':layer,'wkt':plane.wkt})
 def slab(q):
  if q.geom_type=='Polygon' and q.area>1e-6:
   if q.interiors:
    a,b,c,d=q.bounds;m=(a+c)/2
    for qq in [q.intersection(box(a-.01,b-.01,m,d+.01)),q.intersection(box(m-.001,b-.01,c+.01,d+.01))]:slab(qq)
   else:
    pts=[z/.0254 for xy in q.exterior.coords for z in xy];planes.append({'layer':layer,'poly':[pts[0],pts[1],'L',*pts[2:]]})
  elif hasattr(q,'geoms'):
   for qq in q.geoms:slab(qq)
 for x in np.arange(.4,59.6,.5):slab(plane.intersection(box(x,.4,x+.502,69.6)))
 print('GROUND',layer,'area',round(plane.area,2),'islands',len(pieces),flush=True)
(P/'manifests/ground-planes-final-large-v12.json').write_text(json.dumps({'areas':areas,'geometry':actual,'regions':planes},indent=2),encoding='utf-8')
guard=(P/'scripts/read-pcb-pads-v12.js').read_text().split('const out=')[0]
for i in range(0,len(planes),25):
 code=guard+'const regions='+json.dumps(planes[i:i+25])+";const ids=[];for(const r of regions){const p=await eda.pcb_PrimitiveFill.create(r.layer,eda.pcb_MathPolygon.createPolygon(r.poly),'GND',0,undefined,false);if(!p)throw Error('Plane failed');ids.push(p.getState_PrimitiveId());}return {ids,saved:await eda.pcb_Document.save()};"
 (P/f'scripts/apply-ground-planes-final-large-v12-{i//25+1}.js').write_text(code,encoding='utf-8')
print('Ground fill regions',len(planes),'stitch vias',len(newvias),flush=True)
