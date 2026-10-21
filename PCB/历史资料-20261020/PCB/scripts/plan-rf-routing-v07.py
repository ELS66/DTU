from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text().replace('pcb-pads-power-v07.json','pcb-pads-rf-v07.json').replace('routing-power-v07.json','routing-rf-placement-v07.json'))
step=.05;nx=1201;ny=1401
src=Path('PCB/scripts/plan-signals-v07.py').read_text();exec(src[src.index('def maskgeom'):src.index('def route3d')].replace('m[5:696,5:596]=False','m[int(.5/step):int(69.5/step),int(.5/step):int(59.5/step)]=False'))
def route2(net,a,b,width):
 geom=obstacles(net,1);m=maskgeom(geom,width/2+.17);s=(round(a[0]/step),round(a[1]/step));t=(round(b[0]/step),round(b[1]/step));hp=[(math.dist(s,t),0,s)];ds={s:0};prev={}
 while hp:
  _,g,u=heapq.heappop(hp)
  if g!=ds[u]:continue
  if u==t:
   seq=[u]
   while u!=s:u=prev[u];seq.append(u)
   seq=seq[::-1];pts=[list(a)];last=None
   for i in range(1,len(seq)):
    d=(seq[i][0]-seq[i-1][0],seq[i][1]-seq[i-1][1])
    if last is not None and d!=last:pts.append([seq[i-1][0]*step,seq[i-1][1]*step])
    last=d
   pts.append(list(b));line=LineString(pts)
   if line.buffer(width/2+.153).intersects(geom):raise Exception('Actual clearance failed '+net)
   r={'net':net,'layer':1,'widthMm':width,'pointsMm':pts};routes.append(r);tracks.append({'net':net,'layer':1,'geom':line.buffer(width/2)});print(net,'length',round(line.length,3));return
  x,y=u
  for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
   xx,yy=x+dx,y+dy
   if not(0<xx<nx-1 and 0<yy<ny-1) or m[yy,xx]:continue
   if dx and dy and (m[y,xx] or m[yy,x]):continue
   v=(xx,yy);gg=g+(1.41421356 if dx and dy else 1)
   if gg<ds.get(v,1e30):ds[v]=gg;prev[v]=u;heapq.heappush(hp,(gg+math.dist(v,t),gg,v))
 raise Exception('No RF route '+net)
def xy(ref,num):p=next(p for p in pads if p['ref']==ref and p['number']==num);return p['x'],p['y']
routes=[]
for net,a,b,w in [('LTE_ANT',xy('U2','35'),xy('R50','1'),.32),('LTE_ANT',xy('C50','1'),xy('R50','1'),.32),('LTE_RF_FEED',xy('R50','2'),xy('J5','2'),.32),('LTE_RF_FEED',xy('D10','1'),xy('R50','2'),.24),('LTE_RF_FEED',xy('C51','1'),xy('R50','2'),.32)]:route2(net,a,b,w)
# 接地焊盘接出，复用现有过孔；通孔远离焊盘。
newvia=[];ground=[];allpads=unary_union([q['geom'] for q in pads]);obs=obstacles('GND',1);viaobs=unary_union([obstacles('GND',l) for l in [1,2,16]])
for ref in ['C50','C51','D10']:
 q=next(q for q in pads if q['ref']==ref and q['net']=='GND');a=q['x'],q['y'];opts=[]
 for v in vias:
  if v['net']=='GND' and math.dist(a,(v['x'],v['y']))<3 and not LineString([a,(v['x'],v['y'])]).buffer(.2362).intersects(obs):opts.append((math.dist(a,(v['x'],v['y'])),v['x'],v['y'],True))
 for d in [.6,.8,1,1.2,1.5,2,2.5]:
  for i in range(32):
   x,y=a[0]+d*math.cos(i*math.pi/16),a[1]+d*math.sin(i*math.pi/16);g=Point(x,y).buffer(.3)
   if g.intersects(allpads) or g.buffer(.17).intersects(viaobs) or LineString([a,(x,y)]).buffer(.2362).intersects(obs):continue
   if any(math.dist((x,y),(v['x'],v['y']))<.6 for v in vias):continue
   opts.append((d,x,y,False))
 if not opts:raise Exception('No ground escape '+ref)
 _,x,y,existing=min(opts)
 if not existing:newvia.append({'net':'GND','x':x,'y':y,'diameter':.6});vias.append(newvia[-1])
 ground.append({'net':'GND','layer':1,'widthMm':.1524,'pointsMm':[list(a),[x,y]]})
plan={'vias':newvia,'routes':routes+ground};(P/'manifests/rf-routing-plan-v07.json').write_text(json.dumps(plan,indent=2))
guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");'
code=guard+'const plan='+json.dumps(plan)+';for(const v of plan.vias)if(!await eda.pcb_PrimitiveVia.create(v.net,v.x/.0254,v.y/.0254,.3/.0254,.6/.0254,0))throw Error("Via failed");for(const r of plan.routes){const p=r.pointsMm;const z=eda.pcb_MathPolygon.createPolygon([p[0][0]/.0254,p[0][1]/.0254,"L",...p.slice(1).flatMap(q=>q.map(x=>x/.0254))]);if(!await eda.pcb_PrimitivePolyline.create(r.net,r.layer,z,r.widthMm/.0254,false))throw Error("Route failed");}return {saved:await eda.pcb_Document.save()};';(P/'scripts/apply-rf-routing-v07.js').write_text(code)

