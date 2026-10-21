from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text().replace('pcb-pads-power-v07.json','pcb-pads-usb-v07.json').replace('routing-power-v07.json','routing-ground-resume-v07.json'))
step=.05;nx=1201;ny=1401;src=Path('PCB/scripts/plan-signals-v07.py').read_text();exec(src[src.index('def maskgeom'):src.index('def route3d')].replace('m[5:696,5:596]=False','m[int(.4/step):int(69.6/step),int(.4/step):int(59.6/step)]=False'))
new=[];newvia=[];lengths={}
def xy(ref,num):p=next(p for p in pads if p['ref']==ref and p['number']==num);return p['x'],p['y']
def trace(net,a,b,layer,width,role):
 obs=obstacles(net,layer);m=maskgeom(obs,width/2+.158)
 def seed(p):
  x,y=round(p[0]/step),round(p[1]/step);c=[]
  for xx in range(x-4,x+5):
   for yy in range(y-4,y+5):
    if 0<xx<nx-1 and 0<yy<ny-1 and not m[yy,xx] and not LineString([p,(xx*step,yy*step)]).buffer(width/2+.1525).intersects(obs):c.append((math.dist(p,(xx*step,yy*step)),(xx,yy)))
  return min(c)[1] if c else None
 s,t=seed(a),seed(b)
 if s is None or t is None:raise Exception(f'No seed {net} {role} {a} {b}')
 hp=[(math.dist(s,t),0,s)];ds={s:0};prev={}
 while hp:
  _,g,u=heapq.heappop(hp)
  if g!=ds[u]:continue
  if u==t:
   seq=[u]
   while u!=s:u=prev[u];seq.append(u)
   seq=seq[::-1];pts=[list(a),[s[0]*step,s[1]*step]];last=None
   for i in range(1,len(seq)):
    direction=seq[i][0]-seq[i-1][0],seq[i][1]-seq[i-1][1]
    if last is not None and direction!=last:pts.append([seq[i-1][0]*step,seq[i-1][1]*step])
    last=direction
   pts.append([t[0]*step,t[1]*step]);pts.append(list(b));pts=[p for i,p in enumerate(pts) if i==0 or math.dist(p,pts[i-1])>1e-7];line=LineString(pts)
   if line.buffer(width/2+.1524).intersects(obs):raise Exception(f'Actual clearance {net} {role}')
   new.append({'net':net,'layer':layer,'widthMm':width,'pointsMm':pts,'role':role});tracks.append({'net':net,'layer':layer,'geom':line.buffer(width/2)});print(net,role,round(line.length,3),flush=True);return
  x,y=u
  for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
   xx,yy=x+dx,y+dy
   if not(0<xx<nx-1 and 0<yy<ny-1) or m[yy,xx]:continue
   if dx and dy and (m[y,xx] or m[yy,x]):continue
   v=xx,yy;gg=g+(1.41421356 if dx and dy else 1)
   if gg<ds.get(v,1e30):ds[v]=gg;prev[v]=u;heapq.heappush(hp,(gg+math.dist(v,t),gg,v))
 raise Exception(f'No path {net} {role}')

holes=unary_union([Point(q['x'],q['y']).buffer(q['radius']) for q in json.loads((P/'manifests/mechanical-holes-v07.json').read_text())])
original_obstacles=obstacles
def obstacles(net,layer):return unary_union([original_obstacles(net,layer),holes])
trace('SIM_CLK',(1.19888,15.95374),(1.19888,37.2491),1,.1524,'slot-safe')
changed=[];moved=[]
for vid in ['593ebc4c66b123cc','84e0129a1af4f17a']:
 v=next(q for q in old['vias'] if q['id']==vid);a=(v['x']*.0254,v['y']*.0254);b=(.65,a[1]);obs=unary_union([obstacles('SIM_DET',l) for l in [1,2,16]])
 options=[]
 for xx in [.65,.7,.75,.8,.85,.9,1.0,1.1,1.2]:
  for dy in [0,.1,-.1,.2,-.2,.3,-.3,.4,-.4,.5,-.5,.7,-.7,1.,-1.]:
   pt=(xx,a[1]+dy)
   if Point(*pt).buffer(.3+.1524).intersects(obs):continue
   if any(q['id']!=vid and math.dist(pt,(q['x']*.0254,q['y']*.0254))<.61 for q in old['vias']):continue
   if Point(*pt).buffer(.3).intersects(unary_union([q['geom'] for q in pads])):continue
   valid=True
   for q in old['polys']:
    if q['net']!='SIM_DET':continue
    poly=q['polygon'];z=[t for t in poly[3:] if isinstance(t,(int,float))];ps=[(poly[0]*.0254,poly[1]*.0254)]+list(zip([t*.0254 for t in z[::2]],[t*.0254 for t in z[1::2]]))
    if not any(math.dist(p,a)<.00002 for p in ps):continue
    ps=[pt if math.dist(p,a)<.00002 else p for p in ps]
    if LineString(ps).buffer(q['width']*.0254/2+.1524).intersects(obstacles('SIM_DET',q['layer'])):valid=False
   if valid:options.append((math.dist(a,pt),pt))
 if not options:raise Exception('No safe via move')
 b=min(options)[1];print('via',vid,'new',b)
 moved.append({'id':vid,'x':b[0],'y':b[1]})
 for q in old['polys']:
  if q['net']!='SIM_DET':continue
  poly=q['polygon'];z=[x for x in poly[3:] if isinstance(x,(int,float))];ps=[(poly[0]*.0254,poly[1]*.0254)]+list(zip([x*.0254 for x in z[::2]],[x*.0254 for x in z[1::2]]))
  if not any(math.dist(p,a)<.00002 for p in ps):continue
  ps=[b if math.dist(p,a)<.00002 else p for p in ps]
  if LineString(ps).buffer(q['width']*.0254/2+.1524).intersects(obstacles('SIM_DET',q['layer'])):raise Exception('Moved stub collision')
  changed.append({'id':q['id'],'pointsMm':ps})
plan={'route':new[0],'movedVias':moved,'modifiedStubs':changed};(P/'manifests/mechanical-clearance-repair-v07.json').write_text(json.dumps(plan,indent=2))
guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");'
code=guard+'const plan='+json.dumps(plan)+';for(const v of plan.movedVias)if(!await eda.pcb_PrimitiveVia.modify(v.id,{x:v.x/.0254,y:v.y/.0254}))throw Error("Via move failed");for(const z of plan.modifiedStubs){const p=z.pointsMm;const poly=eda.pcb_MathPolygon.createPolygon([p[0][0]/.0254,p[0][1]/.0254,"L",...p.slice(1).flatMap(q=>q.map(v=>v/.0254))]);if(!await eda.pcb_PrimitivePolyline.modify(z.id,{polygon:poly}))throw Error("Stub modify failed");}if(!await eda.pcb_PrimitivePolyline.delete(["0648b62474402ab1"]))throw Error("Delete failed");const z=plan.route;const p=z.pointsMm;const poly=eda.pcb_MathPolygon.createPolygon([p[0][0]/.0254,p[0][1]/.0254,"L",...p.slice(1).flatMap(q=>q.map(v=>v/.0254))]);if(!await eda.pcb_PrimitivePolyline.create(z.net,z.layer,poly,z.widthMm/.0254,false))throw Error("Create failed");return {saved:await eda.pcb_Document.save()};'
(P/'scripts/apply-mechanical-clearance-repair-v07.js').write_text(code)
