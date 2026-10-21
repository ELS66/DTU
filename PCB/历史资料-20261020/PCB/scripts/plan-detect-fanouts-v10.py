from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text().replace('pcb-pads-power-v07.json','pcb-pads-sim-v10.json').replace('routing-power-v07.json','routing-sim-v10.json'))
step=.05;nx=1201;ny=1401;src=Path('PCB/scripts/plan-signals-v07.py').read_text();exec(src[src.index('def maskgeom'):src.index('def route3d')].replace('m[5:696,5:596]=False','m[int(.4/step):int(69.6/step),int(.4/step):int(59.6/step)]=False'))
new=[];newvia=[];lengths={}
def xy(ref,num):p=next(p for p in pads if p['ref']==ref and p['number']==num);return p['x'],p['y']
maskcache={}
def trace(net,a,b,layer,width,role):
 obs=obstacles(net,layer);key=(net,layer,width,len(tracks),len(vias))
 if key not in maskcache:maskcache[key]=maskgeom(obs,width/2+.158)
 m=maskcache[key].copy();ax=int(max(.4,min(a[0],b[0])-2)/step);bx=int(min(59.6,max(a[0],b[0])+2)/step);ay=int(max(.4,min(a[1],b[1])-2)/step);by=int(min(69.6,max(a[1],b[1])+2)/step);m[:ay,:]=True;m[by:,:]=True;m[:,:ax]=True;m[:,bx:]=True
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

holes=unary_union([Point(q['x'],q['y']).buffer(q['radius']) for q in json.loads((P/'manifests/mechanical-holes-v07.json').read_text())]);original=obstacles
def obstacles(net,layer):return unary_union([original(net,layer),holes])

ref=json.loads((P/'manifests/usb-ground-reference-plan-v09.json').read_text());refparts=[]
for q in ref['polygons']:
 nums=[v for v in q if isinstance(v,(int,float))];refparts.append(Polygon([(x*.0254,y*.0254) for x,y in zip(nums[::2],nums[1::2])]))
refgeom=unary_union(refparts);original2=obstacles
def obstacles(net,layer):return unary_union([original2(net,layer)]+([refgeom] if layer==16 and net!='GND' else []))
failed=[];newvias=[]
targets=[('U14','2'),('U14','4'),('U14','6'),('U14','11'),('R101','1'),('R107','1'),('D16','1'),('R100','2'),('C101','1'),('R105','2'),('U12','1')]
for ref,pin in targets:
 q=next(q for q in pads if q['ref']==ref and q['number']==pin);net=q['net'];a=(q['x'],q['y']);obs=unary_union([obstacles(net,l) for l in [1,2,16]]+[p['geom'] for p in pads]);out=[]
 for x in np.arange(a[0]-3,a[0]+3,.2):
  for y in np.arange(a[1]-3,a[1]+3,.2):
   pt=Point(x,y)
   if not(.65<x<59.35 and .65<y<69.35):continue
   if pt.distance(obs)>.46 and all(pt.distance(Point(v['x'],v['y']))>.62 for v in vias):out.append((math.dist(a,(x,y)),(float(x),float(y))))
 found=False
 for _,b in sorted(out)[:18]:
  try:trace(net,a,b,1,.1524,ref+'_'+pin)
  except Exception:continue
  via={'net':net,'x':b[0],'y':b[1],'diameter':.6};newvias.append(via);vias.append(via);found=True;break
 if not found:failed.append(ref+'_'+pin);print('No fanout',ref,pin,flush=True)
 (P/'manifests/detect-fanout-plan-v10.json').write_text(json.dumps({'routes':new,'vias':newvias,'failed':failed},indent=2))
print('summary',len(new),len(newvias),failed,flush=True)
