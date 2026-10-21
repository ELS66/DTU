from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text(encoding='utf-8').replace('routing-power-v07.json','routing-interface-v11.json').replace('pcb-pads-power-v07.json','pcb-pads-interface-v11.json'))
holes=[Point(h['x'],h['y']).buffer(h['radius']+.05) for h in json.loads((P/'manifests/mechanical-holes-v07.json').read_text())]
base_obstacles=obstacles
def obstacles(net,layer):return unary_union([base_obstacles(net,layer),*holes])
source=Path('PCB/scripts/plan-signals-v07.py').read_text(encoding='utf-8')
exec(source[source.index('def maskgeom'):source.index('d=json.loads')].replace('m[5:696,5:596]=False','m[round(.5/step):round(69.5/step),round(.5/step):round(59.5/step)]=False').replace("'diameter':.6","'diameter':.45").replace("1 if l==0 else 2","[1,2,16][l]"))
step=.05;nx=1201;ny=1401;new=[];newvias=[];failed=[]
def label_free_mask(mask):
 lab=np.zeros(mask.shape,dtype=np.int32);parents=[0];previous=[]
 def root(k):
  while parents[k]!=k:parents[k]=parents[parents[k]];k=parents[k]
  return k
 for y,row in enumerate(mask):
  d=np.diff(np.r_[False,~row,False].astype(np.int8));starts=np.flatnonzero(d==1);ends=np.flatnonzero(d==-1);current=[];j=0
  for a,b in zip(starts,ends):
   k=len(parents);parents.append(k);lab[y,a:b]=k;current.append((a,b,k))
   while j<len(previous) and previous[j][1]<=a:j+=1
   jj=j
   while jj<len(previous) and previous[jj][0]<b:
    parents[root(k)]=root(previous[jj][2]);jj+=1
  previous=current
 roots=np.array([root(k) for k in range(len(parents))],dtype=np.int32)
 return roots[lab],len(parents)-1
def groups(net):
 objs=[]
 for p in pads:
  if p['net']==net:objs.append({'geom':p['geom'],'layers':[1,2,15,16] if p['layer']==12 else [p['layer']],'anchors':[(p['x'],p['y'],0 if p['layer']!=2 else 1)],'kind':'pad','ref':p['ref']})
 for t in tracks:
  if t['net']==net:
   x,y=t['geom'].representative_point().coords[0]
   objs.append({'geom':t['geom'],'layers':[t['layer']],'anchors':[(x,y,0 if t['layer']==1 else 1)] if t['layer'] in [1,2] else [],'kind':'track'})
 for v in vias:
  if v['net']==net:objs.append({'geom':Point(v['x'],v['y']).buffer(v['diameter']/2),'layers':[1,2,15,16],'anchors':[(v['x'],v['y'],0),(v['x'],v['y'],1),(v['x'],v['y'],2)],'kind':'via'})
 parent=list(range(len(objs)))
 def root(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 for i,o in enumerate(objs):
  for j in range(i):
   q=objs[j]
   if (set(o['layers']) & set(q['layers']) and o['geom'].distance(q['geom'])<.008) or (net=='GND' and o['kind']=='via' and q['kind']=='via'):parent[root(i)]=root(j)
 out={}
 for i,o in enumerate(objs):out.setdefault(root(i),[]).append(o)
 return [g for g in out.values() if any(o['anchors'] for o in g)]
def findroute(a,b,net,masks,vm):
 global connectivity_masks,connectivity_labels,connectivity_offsets,connectivity_roots
 def seed(p):
  cx,cy=round(p[0]/step),round(p[1]/step);obs=obstacles(net,[1,2,16][p[2]])
  opts=[]
  for x in range(cx-3,cx+4):
   for y in range(cy-3,cy+4):
    if not(0<x<nx-1 and 0<y<ny-1) or masks[p[2]][y,x]:continue
    q=(x*step,y*step)
    if math.dist(p[:2],q)<.25 and LineString([p[:2],q]).distance(obs)>.1524/2+.154:opts.append((math.dist(p[:2],q),(x,y,p[2])))
  return min(opts)[1] if opts else None
 s=seed(a);t=seed(b)
 if s is None or t is None:return None
 if globals().get('connectivity_masks') is not masks:
  labs=[];offsets=[];total=0
  for mask in masks:
   lab,n=label_free_mask(mask);labs.append(lab);offsets.append(total);total+=n+1
  roots=list(range(total))
  def root(k):
   while roots[k]!=k:roots[k]=roots[roots[k]];k=roots[k]
   return k
  for i in range(len(masks)):
   for j in range(i):
    allowed=~vm & ~masks[i] & ~masks[j]
    pairs=np.unique(np.column_stack((labs[i][allowed]+offsets[i],labs[j][allowed]+offsets[j])),axis=0)
    for u,v in pairs:roots[root(int(u))]=root(int(v))
  roots=[root(k) for k in range(total)];connectivity_masks=masks;connectivity_labels=labs;connectivity_offsets=offsets;connectivity_roots=roots
 def region(p):return connectivity_roots[int(connectivity_labels[p[2]][p[1],p[0]])+connectivity_offsets[p[2]]]
 if region(s)!=region(t):return None
 heap=[(math.dist(s[:2],t[:2]),0,s)];dist={s:0};prev={};n=0
 while heap:
  _,cost,u=heapq.heappop(heap)
  if cost!=dist[u]:continue
  if u==t:
   out=[u]
   while u!=s:u=prev[u];out.append(u)
   return out[::-1]
  n+=1
  if n>600000:return None
  x,y,l=u;opts=[]
  for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
   xx=x+dx;yy=y+dy
   if not(0<xx<nx-1 and 0<yy<ny-1) or masks[l][yy,xx]:continue
   if dx and dy and (masks[l][y,xx] or masks[l][yy,x]):continue
   opts.append(((xx,yy,l),1.41421356237 if dx and dy else 1))
  if not vm[y,x]:
   for ll in range(3):
    if ll!=l and not masks[ll][y,x]:opts.append(((x,y,ll),24))
  for v,w in opts:
   g=cost+w
   if g<dist.get(v,1e99):dist[v]=g;prev[v]=u;heapq.heappush(heap,(g+2*math.dist(v[:2],t[:2]),g,v))
 return None
def valid(a,b,seq,net):
 chunks=[];pts=[a[:2],(seq[0][0]*step,seq[0][1]*step)];l=seq[0][2]
 for u,v in zip(seq,seq[1:]):
  p=(v[0]*step,v[1]*step)
  if v[2]!=l:
   if Point(*p).distance(unary_union([obstacles(net,k) for k in [1,2,16]]))<.225+.154:return False
   chunks.append((l,pts));pts=[p];l=v[2]
  else:pts.append(p)
 pts.append(b[:2]);chunks.append((l,pts))
 return all(len(ps)<2 or LineString(ps).distance(obstacles(net,[1,2,16][l]))>.1524/2+.154 for l,ps in chunks)
d=json.loads((P/'reports/pcb-drc-interface-v11.json').read_text(encoding='utf-8-sig'))['result']
sel=[x['name'] for g in d if g.get('name')=='Connection Error' for x in g['list']]
sel.sort(key=lambda n:(0 if n.startswith('232_C') or n in ['232_VPLUS','232_VMINUS'] else 5 if n=='GND' else 4 if n.startswith('LED') else 3,n))
for net in sel:
 gs=groups(net);count=0
 while len(gs)>1:
  anchors=[[a for o in g if o['kind']!='track' or not any(q['kind']!='track' and q['anchors'] for q in g) for a in o['anchors']] for g in gs]
  candidates=sorted((math.dist(a[:2],b[:2])+.8*(a[2]!=b[2]),i,j,a,b) for i in range(len(gs)) for j in range(i) for a in anchors[i] for b in anchors[j])
  masks=[maskgeom(obstacles(net,k),.1524/2+.156) for k in [1,2,16]]
  vm=maskgeom(unary_union([obstacles(net,k) for k in [1,2,16]]+[Point(v['x'],v['y']).buffer(v['diameter']/2) for v in vias]),.225+.17)
  own=unary_union([p['geom'] for p in pads if p['net']==net and p['layer']==1])
  vm|=maskgeom(own,.1+.05)
  for v in vias:
   if v['net']==net:vm[round(v['y']/step),round(v['x']/step)]=False
  for p in pads:
   if p['net']==net and p['layer']==12:vm[round(p['y']/step),round(p['x']/step)]=False
  ok=False;tried=collections.Counter()
  for _,i,j,a,b in candidates[:200]:
   if tried[(i,j)]>=16:continue
   tried[(i,j)]+=1;seq=findroute(a,b,net,masks,vm)
   if seq is None or not valid(a,b,seq,net):
    reverse=findroute(b,a,net,masks,vm)
    if reverse is not None and valid(b,a,reverse,net):a,b=b,a;seq=reverse
   if seq is not None and valid(a,b,seq,net):
    record(net,a[:2],b[:2],seq);gs[j]+=gs.pop(i);count+=1;ok=True;break
  if not ok:failed.append({'net':net,'clusters':len(gs)});break
 print(net,'routed',count,'clusters remaining',len(gs),flush=True)
 (P/'manifests/interface-routing-plan-v11.json').write_text(json.dumps({'routes':new,'vias':newvias,'failed':failed,'nets':sel},indent=2))
guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");'
items=[{'kind':'via',**v} for v in newvias]+[{'kind':'route',**r} for r in new]
for i in range(0,len(items),25):
 code=guard+'const specs='+json.dumps(items[i:i+25])+';const ids=[];for(const z of specs){if(z.kind==="via"){const p=await eda.pcb_PrimitiveVia.create(z.net,z.x/.0254,z.y/.0254,.3/.0254,.6/.0254,0);if(!p)throw Error("Via failed");ids.push(p.getState_PrimitiveId());}else{const p=z.pointsMm;const poly=eda.pcb_MathPolygon.createPolygon([p[0][0]/.0254,p[0][1]/.0254,"L",...p.slice(1).flatMap(q=>q.map(v=>v/.0254))]);const q=await eda.pcb_PrimitivePolyline.create(z.net,z.layer,poly,z.widthMm/.0254,false);if(!q)throw Error("Route failed");ids.push(q.getState_PrimitiveId());}}return {ids,count:specs.length,saved:await eda.pcb_Document.save()};'
 code=code.replace('.3/.0254,.6/.0254','.2/.0254,.45/.0254')
 (P/f'scripts/apply-interface-routing-v11-pass12-{i//25+1}.js').write_text(code)
print('summary routes',len(new),'vias',len(newvias),'failed',failed,flush=True)
