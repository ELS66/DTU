from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text().replace('pcb-pads-power-v07.json','pcb-pads-usb-v07.json').replace('routing-power-v07.json','routing-usb-priority-v07.json'))
step=.05;nx=1201;ny=1401;src=Path('PCB/scripts/plan-signals-v07.py').read_text();exec(src[src.index('def maskgeom'):src.index('def route3d')].replace('m[5:696,5:596]=False','m[int(.4/step):int(69.6/step),int(.4/step):int(59.6/step)]=False'))
new=[];newvia=[];lengths={}
for p in json.loads((P/'manifests/usb-pair-core-v07.json').read_text()):
 if p['label']=='LTE':p['tracksMm']=p['tracksMm'][::-1]
 for net,pts in zip(p['nets'],p['tracksMm']):
  r={'net':net,'layer':p['layer'],'widthMm':.24,'pointsMm':pts,'role':'coupled-core'};new.append(r);tracks.append({'net':net,'layer':p['layer'],'geom':LineString(pts).buffer(.12)})
 lengths[p['label']]={'core':{net:LineString(pts).length for net,pts in zip(p['nets'],p['tracksMm'])}}
cores={p['label']:p for p in json.loads((P/'manifests/usb-pair-core-v07.json').read_text())};cores['LTE']['tracksMm']=cores['LTE']['tracksMm'][::-1]
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
# Air780EPT USB 内部焊盘通过模块焊盘间隙接出，再以底层短差分段跨越外围焊盘。
localnets=['LTE_USB_DP','LTE_USB_DM'];lv={}
for net,where,key in [('LTE_USB_DP',(45.1,35.2),'DP_IN'),('LTE_USB_DM',(45.1,36.4),'DM_IN'),('LTE_USB_DP',(50.0,34.5),'DP_OUT'),('LTE_USB_DM',(49.7,36.4),'DM_OUT')]:
 obs=unary_union([obstacles(net,l) for l in [1,2,16]]);allpads=unary_union([p['geom'] for p in pads]);options=[]
 for dx in [i*.05 for i in range(-6,7)]:
  for dy in [i*.05 for i in range(-6,7)]:
   x,y=where[0]+dx,where[1]+dy;g=Point(x,y).buffer(.3)
   if g.buffer(.16).intersects(obs) or g.intersects(allpads):continue
   options.append((dx*dx+dy*dy,x,y))
 if not options:raise Exception('No LTE input via '+key)
 _,x,y=min(options);v={'net':net,'x':x,'y':y,'diameter':.6};newvia.append(v);vias.append(v);lv[key]=[x,y];print('LTE local via',key,x,y,flush=True)
# 短段同样使用 0.24mm 线宽和 0.16mm 间距。
source=Path('PCB/scripts/plan-usb-core-v07.py').read_text();exec(source[source.index('def path('):source.index('for label,nets,layer,ends')]);obs=unary_union([p['geom'] for p in pads if p['net'] not in localnets and p['layer'] in [2,12]]+[t['geom'] for t in tracks if t['net'] not in localnets and t['layer']==2]+[Point(v['x'],v['y']).buffer(v['diameter']/2) for v in vias if v['net'] not in localnets]);cl=path((45.8,35.8),(49.2,35.8),obs,.51)
if cl is None:raise Exception('No LTE input coupled path')
localcurves=[cl.offset_curve(-.2,join_style=2),cl.offset_curve(.2,join_style=2)]
if any(q.geom_type!='LineString' for q in localcurves) or localcurves[0].distance(localcurves[1])<.3924:raise Exception('LTE input pair geometry')
for net,g in zip(localnets,localcurves):
 if g.buffer(.12+.1524).intersects(obs):raise Exception('LTE local pair clearance')
 new.append({'net':net,'layer':2,'widthMm':.24,'pointsMm':list(g.coords),'role':'coupled-input-core'});tracks.append({'net':net,'layer':2,'geom':g.buffer(.12)})

# ESP 的两颗通孔采用 1mm 间距，避免差分线间距小于通孔外径。
for net,target in [('ESP_USB_DP_EXT',(.7,42)),('ESP_USB_DM_EXT',(1.7,42))]:
 obs=unary_union([obstacles(net,l) for l in [1,2,16]]);allpads=unary_union([p['geom'] for p in pads]);options=[]
 for dx in [i*.1 for i in range(-3,4)]:
  for dy in [i*.1 for i in range(-5,6)]:
   x,y=target[0]+dx,target[1]+dy;g=Point(x,y).buffer(.3)
   if x<.65 or g.buffer(.16).intersects(obs) or g.intersects(allpads):continue
   options.append((dx*dx+dy*dy,x,y))
 if not options:raise Exception('No ESP USB via '+net)
 _,x,y=min(options);v={'net':net,'x':x,'y':y,'diameter':.6};newvia.append(v);vias.append(v);print('via',v)
for label,res,header,esd,layer in [('LTE',['R60','R61'],'J7',['D20','D21'],1),('ESP',['R15','R16'],'J6',['D18','D19'],2)]:
 p=cores[label]
 for k,net in enumerate(p['nets']):
  pts=p['tracksMm'][k]
  if label=='ESP':
   v=next(v for v in newvia if v['net']==net);vxy=v['x'],v['y'];trace(net,xy(res[k],'2'),vxy,1,.2032,'series-to-via');trace(net,vxy,pts[0],2,.24,'via-to-core')
  else:trace(net,xy(res[k],'2'),pts[0],1,.2032,'series-to-core')
  trace(net,pts[-1],xy(header,str(k+2)),layer,.24,'core-to-header');trace(net,xy(esd[k],'1'),xy(header,str(k+2)),1,.2032,'ESD-to-header')
for module,pin,res,net in [('U1','14','R15','ESP_USB_DP'),('U1','13','R16','ESP_USB_DM')]:trace(net,xy(module,pin),xy(res,'1'),1,.2032,'module-to-series')
for k,(net,pin,res,prefix) in enumerate([('LTE_USB_DP','59','R60','DP'),('LTE_USB_DM','60','R61','DM')]):
 trace(net,xy('U2',pin),lv[prefix+'_IN'],1,.2032,'module-to-via');trace(net,lv[prefix+'_IN'],localcurves[k].coords[0],2,.24,'via-to-input-core');trace(net,localcurves[k].coords[-1],lv[prefix+'_OUT'],2,.24,'input-core-to-via');trace(net,lv[prefix+'_OUT'],xy(res,'1'),1,.2032,'via-to-series')
plan={'vias':newvia,'routes':new,'lengths':lengths};(P/'manifests/usb-routing-plan-v07.json').write_text(json.dumps(plan,indent=2))
guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");';code=guard+'const plan='+json.dumps(plan)+';for(const v of plan.vias)if(!await eda.pcb_PrimitiveVia.create(v.net,v.x/.0254,v.y/.0254,.3/.0254,.6/.0254,0))throw Error("Via failed");for(const r of plan.routes){const p=r.pointsMm;const z=eda.pcb_MathPolygon.createPolygon([p[0][0]/.0254,p[0][1]/.0254,"L",...p.slice(1).flatMap(q=>q.map(x=>x/.0254))]);if(!await eda.pcb_PrimitivePolyline.create(r.net,r.layer,z,r.widthMm/.0254,false))throw Error("Route failed");}return {saved:await eda.pcb_Document.save()};';(P/'scripts/apply-usb-routing-v07.js').write_text(code)
