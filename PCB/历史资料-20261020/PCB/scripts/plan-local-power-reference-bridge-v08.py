from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text().replace('pcb-pads-power-v07.json','pcb-pads-gpio-v08.json').replace('routing-power-v07.json','routing-applied-v08.json'))
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
 m[:11,:]=True;m[-11:,:]=True;m[:,:11]=True;m[:,-11:]=True
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

holes=unary_union([Point(q['x'],q['y']).buffer(q['radius']) for q in json.loads((P/'manifests/mechanical-holes-v07.json').read_text())]);original=obstacles
def obstacles(net,layer):return unary_union([original(net,layer),holes])


usb=json.loads((P/'manifests/usb-routing-plan-v07.json').read_text());keepout=unary_union([LineString(r['pointsMm']).buffer(.75) for r in usb['routes'] if r['layer']==2]);base=obstacles
def obstacles(net,layer):return unary_union([base(net,layer),keepout]) if layer==16 else base(net,layer)
obs=unary_union([base('VDD_3V3',l) for l in [1,2,16]]);allpads=unary_union([p['geom'] for p in pads]);chosen=None
for x,y in [(4.3,58.4),(4.6,58.4),(5.0,58.4),(5.4,58.6),(5.0,59.0),(4.4,59.2),(5.5,59.2),(6.0,59.8)]:
 g=Point(x,y).buffer(.3)
 if g.buffer(.16).intersects(obs) or g.intersects(allpads) or g.buffer(.46).intersects(keepout):continue
 if any(math.dist((x,y),(v['x'],v['y']))<.62 for v in vias):continue
 n,t=len(new),len(tracks)
 try:
  trace('VDD_3V3',(4.025,54.725),(x,y),1,.35,'local-reference-bridge')
  trace('VDD_3V3',(x,y),(4.4,64.05),16,.35,'remaining-LED-feed')
 except Exception:
  del new[n:];del tracks[t:];continue
 chosen={'net':'VDD_3V3','x':x,'y':y};break
if chosen is None:raise Exception('No bridge placement')
trace('VDD_3V3',(2.,54.),(3.2,46.45),1,.35,'second-reference-bridge')
plan={'routes':new,'via':chosen,'deletePolys':['6060b374b45e86ac','7649d520ae7f519e']};(P/'manifests/local-power-reference-bridge-v08.json').write_text(json.dumps(plan,indent=2));print('new via',chosen)
guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");'
code=guard+'const plan='+json.dumps(plan)+';if(!await eda.pcb_PrimitivePolyline.delete(plan.deletePolys))throw Error("Delete failed");const v=plan.via;if(!await eda.pcb_PrimitiveVia.create(v.net,v.x/.0254,v.y/.0254,.3/.0254,.6/.0254,0))throw Error("Via failed");for(const r of plan.routes){const p=r.pointsMm;const z=eda.pcb_MathPolygon.createPolygon([p[0][0]/.0254,p[0][1]/.0254,"L",...p.slice(1).flatMap(q=>q.map(v=>v/.0254))]);if(!await eda.pcb_PrimitivePolyline.create(r.net,r.layer,z,r.widthMm/.0254,false))throw Error("Create failed");}return {saved:await eda.pcb_Document.save()};'
(P/'scripts/apply-local-power-reference-bridge-v08.js').write_text(code)
