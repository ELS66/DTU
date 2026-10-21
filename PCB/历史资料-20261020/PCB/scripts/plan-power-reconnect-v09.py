from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text(encoding='utf-8').replace('pcb-pads-power-v07.json','pcb-pads-gpio-v08.json').replace('routing-power-v07.json','routing-start-v09.json'))
step=.05;nx=1201;ny=1401;new=[];newvias=[];failed=[]
def maskgeom(geom,margin):
 region=geom.buffer(margin);m=np.ones((ny,nx),dtype=bool);m[int(.5/step):int(69.5/step),int(.5/step):int(59.5/step)]=False
 for g in list(region.geoms) if hasattr(region,'geoms') else [region]:
  ax,ay,bx,by=g.bounds;x0=max(0,int(ax/step)-1);x1=min(nx,int(bx/step)+2);y0=max(0,int(ay/step)-1);y1=min(ny,int(by/step)+2)
  if x1<=x0 or y1<=y0:continue
  xx,yy=np.meshgrid(np.arange(x0,x1)*step,np.arange(y0,y1)*step);m[y0:y1,x0:x1]|=shapely.contains_xy(g,xx,yy)
 return m
def route3d(a,b,net,masks,viaMask):
 def seed(p):
  anchor=(round(p[0]/step),round(p[1]/step));isvia=any(v['net']==net and math.dist(p,(v['x'],v['y']))<.01 for v in vias);layers=range(3) if isvia else [0];out=[]
  for ll in layers:
   obs=obstacles(net,[1,2,16][ll])
   opts=[]
   for x in range(anchor[0]-3,anchor[0]+4):
    for y in range(anchor[1]-3,anchor[1]+4):
     if 0<x<nx-1 and 0<y<ny-1 and not masks[ll][y,x] and math.dist(p,(x*step,y*step))<.25 and not LineString([p,(x*step,y*step)]).buffer(.1016+.1524).intersects(obs):opts.append((math.dist(p,(x*step,y*step)),(x,y,ll)))
   if opts:out.append(min(opts)[1])
  return out
 ss=seed(a);tt=seed(b)
 if not ss or not tt:return None
 targets=set(tt);t=tt[0];s=ss[0]
 heap=[(math.dist(x[:2],t[:2]),0,x) for x in ss];heapq.heapify(heap);dist={x:0 for x in ss};prev={};n=0;started=time.monotonic()
 while heap:
  _,cost,u=heapq.heappop(heap)
  if cost!=dist[u]:continue
  if u in targets:
   out=[u]
   while u in prev:u=prev[u];out.append(u)
   return out[::-1]
  n+=1
  if n>600000 or time.monotonic()-started>12:return None
  x,y,l=u
  options=[]
  for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
   xx=x+dx;yy=y+dy
   if not(0<xx<nx-1 and 0<yy<ny-1) or masks[l][yy,xx]:continue
   if dx and dy and (masks[l][y,xx] or masks[l][yy,x]):continue
   options.append(((xx,yy,l),1.41421356237 if dx and dy else 1))
  if not viaMask[y,x]:
   for ll in range(3):
    if ll!=l and not masks[ll][y,x]:options.append(((x,y,ll),18))
  for v,w in options:
   g=cost+w
   if g<dist.get(v,1e99):dist[v]=g;prev[v]=u;heapq.heappush(heap,(g+2.2*math.dist(v[:2],t[:2]),g,v))
 return None
def record(net,a,b,seq):
 chunks=[];current=[list(a),[seq[0][0]*step,seq[0][1]*step]];layer=seq[0][2];last=None
 for k in range(1,len(seq)):
  u=seq[k-1];v=seq[k]
  if u[2]!=v[2]:
   point=[u[0]*step,u[1]*step];current.append(point);chunks.append((layer,current));current=[point];layer=v[2];last=None
   if not any(q['net']==net and math.dist(point,(q['x'],q['y']))<.001 for q in vias) and not any(p['net']==net and p['layer']==12 and p['geom'].covers(Point(*point)) for p in pads):
    q={'net':net,'x':point[0],'y':point[1],'diameter':.6};vias.append(q);newvias.append(q)
  else:
   direction=(v[0]-u[0],v[1]-u[1])
   if last is not None and last!=direction:current.append([u[0]*step,u[1]*step])
   last=direction
 current.extend([[seq[-1][0]*step,seq[-1][1]*step],list(b)]);chunks.append((layer,current))
 for l,pts in chunks:
  pts=[pt for i,pt in enumerate(pts) if i==0 or math.dist(pt,pts[i-1])>1e-7]
  if len(pts)<2:continue
  r={'net':net,'layer':[1,2,16][l],'widthMm':.2032,'pointsMm':pts};new.append(r);tracks.append({'net':net,'layer':r['layer'],'geom':LineString(pts).buffer(.2032/2)})

def groups(net):
 ps=[p for p in pads if p['net']==net]; nodes=[(p['geom'],set([1,2,16]) if p['layer']==12 else {p['layer']}) for p in ps]
 nodes +=[(t['geom'],{t['layer']}) for t in tracks if t['net']==net]
 nodes +=[(Point(v['x'],v['y']).buffer(v['diameter']/2),{1,2,16}) for v in vias if v['net']==net]
 parent=list(range(len(nodes)))
 def root(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 for i,(a,la) in enumerate(nodes):
  for j,(b,lb) in enumerate(nodes[:i]):
   if la&lb and a.distance(b)<.001:parent[root(i)]=root(j)
 out={}
 for i,p in enumerate(ps):out.setdefault(root(i),[]).append((p['x'],p['y']))
 ts=[t for t in tracks if t['net']==net];vs=[v for v in vias if v['net']==net]
 for j,v in enumerate(vs):
  rr=root(len(ps)+len(ts)+j)
  if rr in out:out[rr].append((v['x'],v['y']))
 for j,t in enumerate(ts):
  rr=root(len(ps)+j)
  if rr in out and t['layer']==1:
   q=t['geom'].representative_point();out[rr].append((q.x,q.y))
 return [list(set(v)) for v in out.values()]
usb=json.loads((P/'manifests/usb-routing-plan-v07.json').read_text())
reserve=unary_union([LineString(r['pointsMm']).buffer(.75) for r in usb['routes'] if r['layer']==2])
d=json.loads((P/'reports/pcb-drc-with-reference-v08.json').read_text(encoding='utf-8-sig'))['result'];sel=[x['name'] for g in d if g.get('name')=='Connection Error' for x in g['list']]
sel=[n for n in sel if n=='VDD_3V3'];sel.sort(key=lambda n:(0 if n.startswith(('SIM','EFUSE','LTE_')) else 1,n))
original_obstacles=obstacles
holes=unary_union([Point(q['x'],q['y']).buffer(q['radius']) for q in json.loads((P/'manifests/mechanical-holes-v07.json').read_text())])
ref=json.loads((P/'manifests/usb-ground-reference-plan-v08.json').read_text())
refgeoms=[]
for poly in ref['polygons']:
 nums=[x for x in poly if isinstance(x,(float,int))];refgeoms.append(Polygon([(x*.0254,y*.0254) for x,y in zip(nums[::2],nums[1::2])]))
refgeom=unary_union(refgeoms)
def obstacles(net,layer):return unary_union([original_obstacles(net,layer),holes]+([refgeom] if layer==16 and net!='GND' else []))
for net in sel:
 failuresBefore=len(failed);addedBefore=len(new);gg=groups(net);attempted=set();netstart=time.monotonic();tries=0
 while len(gg)>1 and tries<45 and time.monotonic()-netstart<140:
  cand=sorted((math.dist(a,b),i,j,a,b) for i,g in enumerate(gg) for j,h in enumerate(gg[:i]) for a in g for b in h if (a,b) not in attempted)
  if not cand:break
  _,i,j,a,b=cand[0];attempted.add((a,b));tries+=1; masks=[maskgeom(obstacles(net,l) if l!=16 else unary_union([obstacles(net,l),reserve]),.1016+.16) for l in [1,2,16]]
  allobs=unary_union([obstacles(net,l) for l in [1,2,16]]+[p['geom'] for p in pads]+[reserve]);vm=maskgeom(allobs,.3+.16);vm[:13,:]=True;vm[-13:,:]=True;vm[:,:13]=True;vm[:,-13:]=True
  for v in vias:
   x,y=round(v['x']/step),round(v['y']/step)
   for xx in range(max(0,x-14),min(nx,x+15)):
    for yy in range(max(0,y-14),min(ny,y+15)):
     if math.dist((xx*step,yy*step),(v['x'],v['y']))<.62:vm[yy,xx]=True
   if v['net']==net and math.dist((x*step,y*step),(v['x'],v['y']))<.001:vm[y,x]=False
  seq=route3d(a,b,net,masks,vm)
  if seq is None:continue
  n0,v0,t0,va0=len(new),len(newvias),len(tracks),len(vias);record(net,a,b,seq)
  # Verify exact copper clearance before committing this candidate to the plan.
  bad=False
  for r in new[n0:]:
   geom=LineString(r['pointsMm']).buffer(r['widthMm']/2+.1524)
   if geom.intersects(obstacles(net,r['layer'])):bad=True
  for v in newvias[v0:]:
   if Point(v['x'],v['y']).buffer(.3+.1524).intersects(unary_union([obstacles(net,l) for l in [1,2,16]])):bad=True
  if bad:
   del new[n0:];del newvias[v0:];del tracks[t0:];del vias[va0:];continue
  gg=groups(net)
 for g in gg[1:]:failed.append({'net':net,'unconnectedPads':g})
 print(net,'added',len(new)-addedBefore,'remainingComponents',len(gg),flush=True)
 (P/'manifests/power-reconnect-plan-v09.json').write_text(json.dumps({'routes':new,'vias':newvias,'failed':failed,'nets':sel},indent=2))
print('summary',len(new),'routes',len(newvias),'vias',len(failed),'unconnectedComponents',flush=True)
items=[{'kind':'via',**v} for v in newvias]+[{'kind':'route',**r} for r in new]
for i in range(0,len(items),30):
 guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");'
 code=guard+'const specs='+json.dumps(items[i:i+30])+';const ids=[];for(const z of specs){let q;if(z.kind==="via"){q=await eda.pcb_PrimitiveVia.create(z.net,z.x/.0254,z.y/.0254,.3/.0254,.6/.0254,0);}else{const p=z.pointsMm;const poly=eda.pcb_MathPolygon.createPolygon([p[0][0]/.0254,p[0][1]/.0254,"L",...p.slice(1).flatMap(q=>q.map(v=>v/.0254))]);q=await eda.pcb_PrimitivePolyline.create(z.net,z.layer,poly,z.widthMm/.0254,false);}if(!q)throw Error("Create failed");ids.push({kind:z.kind,id:q.getState_PrimitiveId()});}return {ids,saved:await eda.pcb_Document.save()};'
 (P/f'scripts/apply-power-reconnect-v09-{i//30+1}.js').write_text(code)
