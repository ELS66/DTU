from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text(encoding='utf-8'))
f=json.loads((P/'manifests/power-ground-fanout-v07.json').read_text());vias.extend(f['vias']);tracks.extend({'net':r['net'],'layer':r['layer'],'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2)} for r in f['routes']);step=.1;nx=601;ny=701;new=[];fails=[]
def raster(net,layer,width):
 obs=obstacles(net,layer);region=obs.buffer(.18+width/2+.055);m=np.ones((ny,nx),dtype=bool);m[5:696,5:596]=False
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
for net in ['LTE_SW','MCU_SW','TTL_BOOST_SW','LTE_BST','MCU_BST','LTE_FB','TTL_5V_FB']:
 ps=[(q['x'],q['y']) for q in pads if q['net']==net];width=.45 if net.endswith('_SW') else .2032;mask,obs=raster(net,1,width);conn=[ps[0]];rest=ps[1:]
 while rest:
  _,i,j=min((math.dist(a,b),i,j) for i,a in enumerate(conn) for j,b in enumerate(rest));a=conn[i];b=rest.pop(j);pts=astar(a,b,mask)
  if pts is None:fails.append({'net':net,'from':a,'to':b})
  else:add(net,1,pts,width)
  conn.append(b)
 print('local',net,'routes',len(new),'fail',len(fails),flush=True)
for net in ['VIN_485','VIN_232','VIN_TTL','VIN_485_FUSED','VIN_232_FUSED','VIN_TTL_FUSED','VIN_OR','VIN_PROT','VDD_4G','VDD_3V3','VDD_5V_IF']:
 nodes=[(v['x'],v['y']) for v in vias if v['net']==net]+[(q['x'],q['y']) for q in pads if q['net']==net and q['layer']==12];nodes=list(dict.fromkeys(nodes))
 if len(nodes)<2:continue
 mask,obs=raster(net,16,.35);bottom,obsbottom=raster(net,2,.35);conn=[nodes[0]];rest=nodes[1:];n0=len(new)
 while rest:
  _,i,j=min((math.dist(a,b),i,j) for i,a in enumerate(conn) for j,b in enumerate(rest));a=conn[i];b=rest.pop(j);pts=astar(a,b,mask)
  layer=16;edgeobs=obs
  if pts is None:pts=astar(a,b,bottom);layer=2;edgeobs=obsbottom
  if pts is None:fails.append({'net':net,'from':a,'to':b});conn.append(b);continue
  maxwidth=1.2 if net.startswith('VIN') or net=='VDD_4G' else .8
  for a,b in zip(pts,pts[1:]):
   length=math.dist(a,b);n=max(1,math.ceil(length/1.5));last=a
   for k in range(1,n+1):
    end=[a[0]+(b[0]-a[0])*k/n,a[1]+(b[1]-a[1])*k/n];allow=2*(LineString([last,end]).distance(edgeobs)-.175);width=min(maxwidth,math.floor(allow/.05)*.05)
    if width<.3:fails.append({'net':net,'reason':'clearance','width':width});width=.3
    add(net,layer,[list(last),end],round(width,4));last=end
  conn.append(b)
 print('power',net,'newSegments',len(new)-n0,'failed',len(fails),flush=True)
for bad in f['failed']:
 q=next(q for q in pads if q['ref']+':'+q['number']==bad['pad']);net=q['net'];a=(q['x'],q['y']);targets=sorted([(v['x'],v['y']) for v in vias if v['net']==net],key=lambda b:math.dist(a,b));mask,obs=raster(net,1,.2032)
 for b in targets[:12]:
  pts=astar(a,b,mask)
  if pts:add(net,1,pts,.2032);break
 else:fails.append({'stage':'fanout repair','net':net,'pad':bad['pad']})
plan={'routes':new,'failed':fails,'thinLongPowerSegments':[r for r in new if r['layer']==16 and r['widthMm']<.6 and math.dist(r['pointsMm'][0],r['pointsMm'][-1])>1.45]};(P/'manifests/power-routing-v07.json').write_text(json.dumps(plan,indent=2));print('summary',len(new),'failed',fails,'narrow',len(plan['thinLongPowerSegments']),flush=True)
guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");'
for i in range(0,len(new),40):
 code=guard+'const specs='+json.dumps(new[i:i+40])+';for(const z of specs){const pts=z.pointsMm;const p=[pts[0][0]/.0254,pts[0][1]/.0254,"L",...pts.slice(1).flatMap(q=>q.map(v=>v/.0254))];if(!await eda.pcb_PrimitivePolyline.create(z.net,z.layer,eda.pcb_MathPolygon.createPolygon(p),z.widthMm/.0254,false))throw Error("Route failed");}return {count:specs.length,saved:await eda.pcb_Document.save()};';(P/f'scripts/apply-power-routes-v07-{i//40+1}.js').write_text(code)

