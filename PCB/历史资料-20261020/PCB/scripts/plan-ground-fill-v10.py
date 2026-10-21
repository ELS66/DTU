from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text().replace('routing-power-v07.json','routing-final-v10.json').replace('pcb-pads-power-v07.json','pcb-pads-final-v10.json'))
import zipfile
z=zipfile.ZipFile('PCB/eda/DTU-V0.6-精简完成.epro2');ss=z.read(next(n for n in z.namelist() if n.endswith('.epru'))).decode();lib={};doc=None
for line in ss.splitlines():
 if '||' not in line:continue
 a,b=line.split('||',1)
 try:h=json.loads(a);v=json.loads(b.rstrip('|'))
 except:continue
 if h['type']=='DOCHEAD':doc=v.get('uuid');lib.setdefault(doc,[])
 if doc:lib[doc].append((h,v))
records=json.loads((P/'reports/pcb-records-v07.json').read_text());fps={v['parentId']:v['value'] for h,v in records if h['type']=='ATTR' and v.get('key')=='Footprint'};holes=[]
for h,c in records:
 if h['type']!='COMPONENT':continue
 for hh,v in lib.get(fps.get(h['id']),[]):
  if hh['type']!='FILL' or v.get('layerId')!=12:continue
  q=v['path'];ang=math.radians(c['angle'])
  if q[0]=='CIRCLE':
   xx=(c['x']+q[1]*math.cos(ang)-q[2]*math.sin(ang))*.0254;yy=(c['y']+q[1]*math.sin(ang)+q[2]*math.cos(ang))*.0254;geom=Point(xx,yy).buffer(q[3]*.0254,quad_segs=24);holes.append({'id':h['id']+hh['id'],'x':xx,'y':yy,'radius':q[3]*.0254,'geom':geom})
print('slots', [{k:v for k,v in h.items() if k!='geom'} for h in holes]);(P/'manifests/mechanical-holes-v07.json').write_text(json.dumps([{k:v for k,v in h.items() if k!='geom'} for h in holes],indent=2))
obs=[Point(v['x'],v['y']).buffer((v['diameter']/2+.28)/math.cos(math.pi/32),quad_segs=8) for v in vias if v['net']!='GND']+[p['geom'].buffer(.28,quad_segs=8) for p in pads if p['layer']==12 and p['net']!='GND']+[h['geom'].buffer(.3,quad_segs=8) for h in holes]
plane=box(.4,.4,59.6,69.6).difference(unary_union(obs));parts=list(plane.geoms) if hasattr(plane,'geoms') else [plane];parts=[g for g in parts if any(g.intersects(Point(v['x'],v['y']).buffer(.25)) for v in vias if v['net']=='GND')];plane=unary_union(parts);out=[]
for i in range(75):
 strip=box(.4+i*.8,.4,min(59.6,.4+(i+1)*.8+.002),69.6).intersection(plane)
 for g in list(strip.geoms) if hasattr(strip,'geoms') else [strip]:
  if g.geom_type!='Polygon' or g.area<.0001:continue
  if len(g.interiors):raise Exception('Interior hole in slab')
  pts=[[round(x/.0254,4),round(y/.0254,4)] for x,y in g.exterior.coords];out.append([*pts[0],'L',*[t for q in pts[1:] for t in q]])
(P/'manifests/ground-fill-plan-v10.json').write_text(json.dumps({'layer':15,'net':'GND','areaMm2':plane.area,'polygons':out},indent=2));guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");'
for i in range(0,len(out),15):
 code=guard+'const ps='+json.dumps(out[i:i+15])+';const ids=[];for(const a of ps){const p=await eda.pcb_PrimitiveFill.create(15,eda.pcb_MathPolygon.createPolygon(a),"GND",0,undefined,false);if(!p)throw Error("Fill failed");ids.push(p.getState_PrimitiveId());}return {ids,saved:await eda.pcb_Document.save()};';(P/f'scripts/apply-ground-fill-v10-{i//15+1}.js').write_text(code)
print('plane area',plane.area,'polygons',len(out),'batches',math.ceil(len(out)/15))
