from pathlib import Path
s=Path('PCB/scripts/plan-interface-routing-v11.py').read_text();exec(s[:s.rindex('d=json.loads')]);new=[];newvias=[];failed=[]
targets=json.loads(Path(sys.argv[1]).read_text()) if len(sys.argv)>1 else [('U7',n) for n in ['11','12','13','14']]+[('U1','11'),('D34','1'),('U1','25'),('D36','1'),('U1','26'),('D35','1'),('R30','2')]
for ref,num in targets:
 p=next(p for p in pads if p['ref']==ref and p['number']==num);net=p['net'];a=(p['x'],p['y']);top=obstacles(net,1);ob=unary_union([obstacles(net,k) for k in [1,2,16]]+[Point(v['x'],v['y']).buffer(v['diameter']/2) for v in vias]);own=unary_union([q['geom'] for q in pads if q['layer']==1]);mask=maskgeom(top,.0762+.17);vm=maskgeom(ob,.225+.17)|maskgeom(own,.1+.05)
 cx,cy=round(a[0]/step),round(a[1]/step);opts=[]
 for x in range(cx-3,cx+4):
  for y in range(cy-3,cy+4):
   if not mask[y,x] and LineString([a,(x*step,y*step)]).distance(top)>.0762+.154:opts.append((math.dist(a,(x*step,y*step)),(x,y)))
 if not opts:failed.append([ref,num,'seed']);continue
 start=min(opts)[1];hp=[(0,start)];ds={start:0};prev={};end=None
 while hp:
  g,u=heapq.heappop(hp)
  if g!=ds[u]:continue
  x,y=u
  if math.dist(a,(x*step,y*step))>8:continue
  if not vm[y,x]:end=u;break
  for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
   xx,yy=x+dx,y+dy
   if not(0<xx<nx-1 and 0<yy<ny-1) or mask[yy,xx] or (dx and dy and (mask[y,xx] or mask[yy,x])):continue
   v=(xx,yy);gg=g+(1.41421356 if dx and dy else 1)
   if gg<ds.get(v,1e30):ds[v]=gg;prev[v]=u;heapq.heappush(hp,(gg,v))
 if end is None:failed.append([ref,num,'no dogbone']);print('failed',ref,num,flush=True);continue
 seq=[end];u=end
 while u!=start:u=prev[u];seq.append(u)
 seq=seq[::-1];point=(end[0]*step,end[1]*step);record(net,a,point,[(x,y,0) for x,y in seq]);v={'net':net,'x':point[0],'y':point[1],'diameter':.45};vias.append(v);newvias.append(v);print('fanout',ref,num,point,flush=True)
plan={'routes':new,'vias':newvias,'failed':failed};(P/'manifests/fanout-plan-v11.json').write_text(json.dumps(plan,indent=2));guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");';items=[{'kind':'via',**v} for v in newvias]+[{'kind':'route',**r} for r in new];code=guard+'const specs='+json.dumps(items)+';const ids=[];for(const z of specs){const q=z.kind==="via"?await eda.pcb_PrimitiveVia.create(z.net,z.x/.0254,z.y/.0254,.2/.0254,.45/.0254,0):await eda.pcb_PrimitivePolyline.create(z.net,z.layer,eda.pcb_MathPolygon.createPolygon([z.pointsMm[0][0]/.0254,z.pointsMm[0][1]/.0254,"L",...z.pointsMm.slice(1).flatMap(p=>p.map(v=>v/.0254))]),z.widthMm/.0254,false);if(!q)throw Error("Fanout failed");ids.push(q.getState_PrimitiveId());}return {ids,saved:await eda.pcb_Document.save()};';(P/'scripts/apply-fanout-v11.js').write_text(code)
print('Failed',failed,flush=True)
