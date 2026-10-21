"""Actual-copper geometric routing helpers; all dimensions in mm."""
import sys,json,math,heapq,time,collections
from pathlib import Path
sys.path.insert(0,str(Path('PCB/.tools').resolve()))
import numpy as np
import shapely
from shapely.geometry import box,Point,Polygon,LineString
from shapely.ops import unary_union
from shapely.affinity import rotate,translate
P=Path('PCB');cs=json.load(open(P/'manifests/read-pcb-pads-v13.json',encoding='utf-8'))['result'];by={c['ref']:c for c in cs};pads=[];tracks=[];vias=[];new=[];newvias=[]
for c in cs:
 for p in c['pads']:
  q={**p,'ref':c['ref'],'x':p['x']*.0254,'y':p['y']*.0254}
  if p['shape'][0]=='POLYGON':
   v=[z*.0254 for z in p['shape'][1] if isinstance(z,(int,float))];g=Polygon(list(zip(v[::2],v[1::2])))
  else:
   w,h=[z*.0254 for z in p['shape'][1:3]];g=box(-w/2,-h/2,w/2,h/2)
   if p['shape'][0]=='ELLIPSE':g=Point(0,0).buffer(max(w,h)/2)
   g=translate(rotate(g,p['rotation'],origin=(0,0)),q['x'],q['y'])
  q['geom']=g;pads.append(q)
holes=[Point(x,y).buffer(3.4,quad_segs=24) for x,y in [(4,4),(56,4),(4,66),(56,66)]]
# SIM holder has two non-plated alignment holes, 0.75 mm diameter.
for local in [(-196.845,-213.47),(137.795,-213.47)]:
 c=by['J4'];a=math.radians(c['rotation']);x=(c['x']+local[0]*math.cos(a)-local[1]*math.sin(a))*.0254;y=(c['y']+local[0]*math.sin(a)+local[1]*math.cos(a))*.0254
 holes.append(Point(x,y).buffer(.375+.15,quad_segs=24))
step=.1;nx=601;ny=701;layers=[1,2,16]
def xy(ref,pin):
 q=next(p for p in pads if p['ref']==ref and p['number']==pin);return q['x'],q['y']
def obstacles(net,layer,ignore=()):
 return unary_union([p['geom'] for p in pads if p['net']!=net and p['net'] not in ignore and p['layer'] in [layer,12]]+[t['geom'] for t in tracks if t['net']!=net and t['net'] not in ignore and t['layer']==layer]+[Point(v['x'],v['y']).buffer(v['diameter']/2) for v in vias if v['net']!=net and v['net'] not in ignore]+holes)
def maskgeom(g,margin):
 region=g.buffer(margin);m=np.ones((ny,nx),dtype=bool);m[round(.5/step):round(69.5/step)+1,round(.5/step):round(59.5/step)+1]=False
 for q in list(region.geoms) if hasattr(region,'geoms') else [region]:
  if q.is_empty:continue
  a,b,c,d=q.bounds;x0=max(0,int(a/step)-1);x1=min(nx,int(c/step)+2);y0=max(0,int(b/step)-1);y1=min(ny,int(d/step)+2)
  if x1>x0 and y1>y0:
   x,y=np.meshgrid(np.arange(x0,x1)*step,np.arange(y0,y1)*step);m[y0:y1,x0:x1]|=shapely.contains_xy(q,x,y)
 return m
def route(net,a,b,width=.1524,allowed=(1,2,16),limit=40000):
 obs=[obstacles(net,k) for k in allowed];masks=[maskgeom(o,width/2+.158) for o in obs]
 allobs=unary_union([obstacles(net,k) for k in layers]+[p['geom'].buffer(.04) for p in pads if p['net']==net]+[Point(v['x'],v['y']).buffer(v['diameter']/2) for v in vias]);vm=maskgeom(allobs,.225+.16)
 for v in vias:
  if v['net']==net:vm[round(v['y']/step),round(v['x']/step)]=False
 for p in pads:
  if p['net']==net and p['layer']==12:vm[round(p['y']/step),round(p['x']/step)]=False
 def seed(p):
  ls=range(len(allowed)) if p[2]==12 else [allowed.index(p[2])] if p[2] in allowed else []
  opts=[];cx,cy=round(p[0]/step),round(p[1]/step)
  for l in ls:
   for x in range(cx-4,cx+5):
    for y in range(cy-4,cy+5):
     if not (0<x<nx-1 and 0<y<ny-1) or masks[l][y,x]:continue
     q=(x*step,y*step)
     if math.dist(p[:2],q)<.27 and LineString([p[:2],q]).distance(obs[l])>width/2+.153:opts.append((math.dist(p[:2],q),(x,y,l)))
  return [o[1] for o in sorted(opts)]
 starts,targets=seed(a),seed(b)
 if not starts or not targets:return None
 targetset=set(targets);startset=set(starts);t=targets[0]
 hp=[(min(math.dist(s[:2],q[:2]) for q in targets),0,s) for s in starts];heapq.heapify(hp);ds={s:0 for s in starts};prev={};count=0
 while hp:
  _,cost,u=heapq.heappop(hp)
  if cost!=ds[u]:continue
  if u in targetset:
   t=u;seq=[u]
   while u not in startset:u=prev[u];seq.append(u)
   seq=seq[::-1];chunks=[];pts=[list(a[:2]),[seq[0][0]*step,seq[0][1]*step]];l=seq[0][2];last=None;vs=[]
   for u,v in zip(seq,seq[1:]):
    if u[2]!=v[2]:
     pt=[u[0]*step,u[1]*step];pts.append(pt);chunks.append((l,pts));pts=[pt];l=v[2];last=None;vs.append(pt)
    else:
     direction=(v[0]-u[0],v[1]-u[1])
     if last is not None and direction!=last:pts.append([u[0]*step,u[1]*step])
     last=direction
   pts +=[[t[0]*step,t[1]*step],list(b[:2])];chunks.append((l,pts));out=[]
   for l,pts in chunks:
    pts=[p for i,p in enumerate(pts) if i==0 or math.dist(p,pts[i-1])>1e-7]
    if len(pts)<2:continue
    line=LineString(pts)
    if line.distance(obs[l])<width/2+.153:return None
    out.append({'net':net,'layer':allowed[l],'widthMm':width,'pointsMm':pts})
   return out,vs
  count+=1
  if count>limit:return None
  x,y,l=u;opts=[]
  for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
   xx,yy=x+dx,y+dy
   if not(0<xx<nx-1 and 0<yy<ny-1) or masks[l][yy,xx]:continue
   if dx and dy and (masks[l][y,xx] or masks[l][yy,x]):continue
   opts.append(((xx,yy,l),math.sqrt(2) if dx and dy else 1))
  if not vm[y,x]:
   for ll in range(len(allowed)):
    if ll!=l and not masks[ll][y,x]:opts.append(((x,y,ll),30))
  for v,w in opts:
   g=cost+w
   if g<ds.get(v,1e50):ds[v]=g;prev[v]=u;heapq.heappush(hp,(g+2.0*math.dist(v[:2],t[:2]),g,v))
 return None
def addroute(net,a,b,width=.1524,allowed=(1,2,16)):
 result=route(net,a,b,width,allowed)
 if result is None:return False
 rs,vs=result
 for r in rs:new.append(r);tracks.append({'net':net,'layer':r['layer'],'geom':LineString(r['pointsMm']).buffer(width/2),'points':r['pointsMm']})
 for x,y in vs:
  if not any(v['net']==net and math.dist((x,y),(v['x'],v['y']))<.05 for v in vias) and not any(p['net']==net and p['layer']==12 and p['geom'].covers(Point(x,y)) for p in pads):
   v={'net':net,'x':x,'y':y,'diameter':.45,'hole':.2};vias.append(v);newvias.append(v)
 return True
def addline(net,layer,pts,width=.1524):
 if LineString(pts).distance(obstacles(net,layer))<width/2+.153:return False
 r={'net':net,'layer':layer,'widthMm':width,'pointsMm':pts};new.append(r);tracks.append({'net':net,'layer':layer,'geom':LineString(pts).buffer(width/2),'points':pts});return True
def addvia(net,target,diameter=.45,hole=.2,source=None,source_layer=1,width=.1524):
 obs=unary_union([obstacles(net,k) for k in layers]+[p['geom'] for p in pads]+[Point(v['x'],v['y']).buffer(v['diameter']/2) for v in vias]);opts=[]
 for radius in [0,.2,.4,.6,.8,1,1.2,1.5,1.8,2.2,2.8,3.5,4.5]:
  for i in range(32):
   x=round((target[0]+radius*math.cos(i*math.pi/16))/.05)*.05;y=round((target[1]+radius*math.sin(i*math.pi/16))/.05)*.05
   if x<.75 or x>59.25 or y<.75 or y>69.25 or Point(x,y).distance(obs)<diameter/2+.16:continue
   if source and LineString([source,(x,y)]).distance(obstacles(net,source_layer))<width/2+.153:continue
   opts.append((radius,x,y))
  if opts:break
 if not opts:return None
 _,x,y=min(opts);v={'net':net,'x':x,'y':y,'diameter':diameter,'hole':hole};vias.append(v);newvias.append(v)
 if source and not addline(net,source_layer,[source,(x,y)],width):raise Exception('Via source not connected')
 return (x,y)
def load_plan(path):
 a=json.load(open(path,encoding='utf-8'))
 for r in a.get('routes',[]):tracks.append({'net':r['net'],'layer':r['layer'],'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2),'points':r['pointsMm']})
 vias.extend(a.get('vias',[]))
 return a
def save_plan(name,failed=()):
 plan={'routes':new,'vias':newvias,'failed':failed};(P/f'manifests/{name}.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
 guard=(P/'scripts/read-pcb-pads-v13.js').read_text().split('const out=')[0];enums='const EPCB_LayerId={TOP:1,BOTTOM:2,INNER_1:15,INNER_2:16};const EPCB_PrimitiveViaType={VIA:0};'
 items=[{'kind':'via',**v} for v in newvias]+[{'kind':'route',**r} for r in new]
 for k in range(0,len(items),30):
  code=guard+enums+'const items='+json.dumps(items[k:k+30])+";const ids=[];for(const z of items){let p;if(z.kind==='via'){p=await eda.pcb_PrimitiveVia.create(z.net,z.x/.0254,z.y/.0254,z.hole/.0254,z.diameter/.0254,EPCB_PrimitiveViaType.VIA);}else{const a=z.pointsMm;const poly=eda.pcb_MathPolygon.createPolygon([a[0][0]/.0254,a[0][1]/.0254,'L',...a.slice(1).flatMap(q=>q.map(v=>v/.0254))]);const layer=z.layer;p=await eda.pcb_PrimitivePolyline.create(z.net,layer,poly,z.widthMm/.0254,false);}if(!p)throw Error('Route creation failed');ids.push(p.getState_PrimitiveId());}return {ids,saved:await eda.pcb_Document.save()};"
  (P/f'scripts/apply-{name}-{k//30+1}.js').write_text(code,encoding='utf-8')
 print(name,'routes',len(new),'vias',len(newvias),'failed',failed,flush=True)
