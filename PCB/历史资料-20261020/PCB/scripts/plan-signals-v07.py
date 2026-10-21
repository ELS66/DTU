from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text(encoding='utf-8').replace('routing-power-v07.json','routing-pre-signals-v07.json'))
step=.1;nx=601;ny=701;new=[];newvias=[];failed=[]
def maskgeom(geom,margin):
 region=geom.buffer(margin);m=np.ones((ny,nx),dtype=bool);m[5:696,5:596]=False
 for g in list(region.geoms) if hasattr(region,'geoms') else [region]:
  ax,ay,bx,by=g.bounds;x0=max(0,int(ax/step)-1);x1=min(nx,int(bx/step)+2);y0=max(0,int(ay/step)-1);y1=min(ny,int(by/step)+2)
  if x1<=x0 or y1<=y0:continue
  xx,yy=np.meshgrid(np.arange(x0,x1)*step,np.arange(y0,y1)*step);m[y0:y1,x0:x1]|=shapely.contains_xy(g,xx,yy)
 return m
def route3d(a,b,net,masks,viaMask):
 def seed(p):
  s=(round(p[0]/step),round(p[1]/step));opts=[(math.dist(p,(x*step,y*step)),(x,y,0)) for x in range(s[0]-2,s[0]+3) for y in range(s[1]-2,s[1]+3) if 0<x<nx-1 and 0<y<ny-1 and not masks[0][y,x] and math.dist(p,(x*step,y*step))<.25];return min(opts)[1] if opts else None
 s=seed(a);t=seed(b)
 if s is None or t is None:return None
 heap=[(math.dist(s[:2],t[:2]),0,s)];dist={s:0};prev={};n=0
 while heap:
  _,cost,u=heapq.heappop(heap)
  if cost!=dist[u]:continue
  if u==t:
   out=[u]
   while u!=s:u=prev[u];out.append(u)
   return out[::-1]
  n+=1
  if n>280000:return None
  x,y,l=u
  options=[]
  for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
   xx=x+dx;yy=y+dy
   if not(0<xx<nx-1 and 0<yy<ny-1) or masks[l][yy,xx]:continue
   if dx and dy and (masks[l][y,xx] or masks[l][yy,x]):continue
   options.append(((xx,yy,l),1.41421356237 if dx and dy else 1))
  if not viaMask[y,x] and not masks[1-l][y,x]:options.append(((x,y,1-l),18))
  for v,w in options:
   g=cost+w
   if g<dist.get(v,1e99):dist[v]=g;prev[v]=u;heapq.heappush(heap,(g+math.dist(v[:2],t[:2]),g,v))
 return None
def record(net,a,b,seq):
 chunks=[];current=[list(a),[seq[0][0]*step,seq[0][1]*step]];layer=seq[0][2];last=None
 for k in range(1,len(seq)):
  u=seq[k-1];v=seq[k]
  if u[2]!=v[2]:
   point=[u[0]*step,u[1]*step];current.append(point);chunks.append((layer,current));current=[point];layer=v[2];last=None
   if not any(q['net']==net and math.dist(point,(q['x'],q['y']))<.22 for q in vias) and not any(p['net']==net and p['layer']==12 and p['geom'].covers(Point(*point)) for p in pads):
    q={'net':net,'x':point[0],'y':point[1],'diameter':.6};vias.append(q);newvias.append(q)
  else:
   direction=(v[0]-u[0],v[1]-u[1])
   if last is not None and last!=direction:current.append([u[0]*step,u[1]*step])
   last=direction
 current.extend([[seq[-1][0]*step,seq[-1][1]*step],list(b)]);chunks.append((layer,current))
 for l,pts in chunks:
  pts=[pt for i,pt in enumerate(pts) if i==0 or math.dist(pt,pts[i-1])>1e-7]
  if len(pts)<2:continue
  r={'net':net,'layer':1 if l==0 else 2,'widthMm':.1524,'pointsMm':pts};new.append(r);tracks.append({'net':net,'layer':r['layer'],'geom':LineString(pts).buffer(.1524/2)})
d=json.loads((P/'reports/pcb-drc-pre-signals-v07.json').read_text(encoding='utf-8-sig'))['result'];sel=[x['name'] for g in d if g.get('name')=='Connection Error' for x in g['list']];sel=[n for n in sel if n not in ['GND','LTE_ANT','LTE_RF_FEED','LTE_FB','TTL_5V_FB'] and not n.startswith(('VIN','VDD')) and not any(z in n for z in ['_USB','_SW','_BST'])];sel.sort(key=lambda n:(0 if n in ['POWER_FAULT_N','Q1_BASE','Q2_BASE'] else 1 if n.startswith('LED') and n.endswith('_A') else 2 if n.startswith('SIM') else 3,n))
for net in sel:
 mask1=maskgeom(obstacles(net,1),.1524/2+.205);mask2=maskgeom(obstacles(net,2),.1524/2+.205);allobs=unary_union([obstacles(net,1),obstacles(net,2),obstacles(net,16),unary_union([p['geom'] for p in pads if p['net']==net and p['layer']==1])]);viamask=maskgeom(allobs,.3+.205)
 for v in vias:
  if v['net']!=net:continue
  x=round(v['x']/step);y=round(v['y']/step)
  for xx in range(x-1,x+2):
   for yy in range(y-1,y+2):
    if 0<xx<nx-1 and 0<yy<ny-1 and math.dist((xx*step,yy*step),(v['x'],v['y']))<.2:viamask[yy,xx]=False
 for p in pads:
  if p['net']==net and p['layer']==12:
   x=round(p['x']/step);y=round(p['y']/step);viamask[y,x]=False
 ps=[(p['x'],p['y']) for p in pads if p['net']==net];conn=[ps[0]];rest=ps[1:];count=0
 while rest:
  _,i,j=min((math.dist(a,b),i,j) for i,a in enumerate(conn) for j,b in enumerate(rest));a=conn[i];b=rest.pop(j);seq=route3d(a,b,net,[mask1,mask2],viamask)
  if seq is None:failed.append({'net':net,'from':a,'to':b})
  else:record(net,a,b,seq);count+=1
  conn.append(b)
 print('signal',net,'connections',count,'failures',sum(z['net']==net for z in failed),flush=True)
 plan={'routes':new,'vias':newvias,'failed':failed,'nets':sel};(P/'manifests/signal-routing-plan-v07.json').write_text(json.dumps(plan,indent=2))
print('summary',len(sel),'nets',len(new),'routes',len(newvias),'vias','failed',failed,flush=True)
guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");'
items=[{'kind':'via',**v} for v in newvias]+[{'kind':'route',**r} for r in new]
for i in range(0,len(items),35):
 code=guard+'const specs='+json.dumps(items[i:i+35])+';for(const z of specs){if(z.kind==="via"){if(!await eda.pcb_PrimitiveVia.create(z.net,z.x/.0254,z.y/.0254,.3/.0254,.6/.0254,0))throw Error("Via failed");}else{const p=z.pointsMm;const poly=eda.pcb_MathPolygon.createPolygon([p[0][0]/.0254,p[0][1]/.0254,"L",...p.slice(1).flatMap(q=>q.map(v=>v/.0254))]);if(!await eda.pcb_PrimitivePolyline.create(z.net,z.layer,poly,z.widthMm/.0254,false))throw Error("Route failed");}}return {count:specs.length,saved:await eda.pcb_Document.save()};';(P/f'scripts/apply-signals-v07-{i//35+1}.js').write_text(code)
