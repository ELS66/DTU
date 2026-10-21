from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text(encoding='utf-8').replace('routing-power-v07.json','routing-after-power-v07.json'))
f=json.loads((P/'manifests/power-ground-fanout-v07.json').read_text());vias.extend(f['vias']);tracks.extend({'net':r['net'],'layer':r['layer'],'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2)} for r in f['routes']);step=.05;nx=1201;ny=1401;new=[];fails=[]
def raster(net,layer,width):
 obs=obstacles(net,layer);region=obs.buffer(.18+width/2+.055);m=np.ones((ny,nx),dtype=bool);m[9:1392,9:1192]=False
 geoms=list(region.geoms) if hasattr(region,'geoms') else [region]
 for g in geoms:
  ax,ay,bx,by=g.bounds;x0=max(0,int(ax/step)-1);x1=min(nx,int(bx/step)+2);y0=max(0,int(ay/step)-1);y1=min(ny,int(by/step)+2)
  if x1<=x0 or y1<=y0:continue
  xx,yy=np.meshgrid(np.arange(x0,x1)*step,np.arange(y0,y1)*step);m[y0:y1,x0:x1]|=shapely.contains_xy(g,xx,yy)
 return m,obs
def astar(a,b,m):
 s=(round(a[0]/step),round(a[1]/step));t=(round(b[0]/step),round(b[1]/step))
 def seed(pt,cell):
  if not m[cell[1],cell[0]]:return cell
  opts=[(math.dist(pt,(x*step,y*step)),(x,y)) for x in range(cell[0]-2,cell[0]+3) for y in range(cell[1]-2,cell[1]+3) if 0<x<nx-1 and 0<y<ny-1 and not m[y,x] and math.dist(pt,(x*step,y*step))<.25]
  return min(opts)[1] if opts else None
 s=seed(a,s);t=seed(b,t)
 if s is None or t is None:return None
 heap=[(math.dist(s,t),0,s)];dist={s:0};prev={};n=0
 while heap:
  _,g,u=heapq.heappop(heap)
  if g!=dist[u]:continue
  if u==t:
   seq=[u]
   while u!=s:u=prev[u];seq.append(u)
   seq=seq[::-1];out=[list(a),[s[0]*step,s[1]*step]];last=None
   for k in range(1,len(seq)):
    d=(seq[k][0]-seq[k-1][0],seq[k][1]-seq[k-1][1])
    if last is not None and d!=last:out.append([seq[k-1][0]*step,seq[k-1][1]*step])
    last=d
   out.extend([[t[0]*step,t[1]*step],list(b)]);return [q for i,q in enumerate(out) if i==0 or math.dist(q,out[i-1])>1e-6]
  n+=1
  if n>350000:return None
  for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
   v=(u[0]+dx,u[1]+dy)
   if not(0<v[0]<nx-1 and 0<v[1]<ny-1) or m[v[1],v[0]]:continue
   if dx and dy and (m[u[1],v[0]] or m[v[1],u[0]]):continue
   gg=g+(1.41421356237 if dx and dy else 1)
   if gg<dist.get(v,1e99):dist[v]=gg;prev[v]=u;heapq.heappush(heap,(gg+math.dist(v,t),gg,v))
 return None
def add(net,layer,pts,width):
 if new and new[-1]['net']==net and new[-1]['layer']==layer and new[-1]['widthMm']==width and math.dist(new[-1]['pointsMm'][-1],pts[0])<1e-8:new[-1]['pointsMm'].extend(pts[1:])
 else:new.append({'net':net,'layer':layer,'pointsMm':pts,'widthMm':width})
 tracks.append({'net':net,'layer':layer,'geom':LineString(pts).buffer(width/2)})
