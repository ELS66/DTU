from pathlib import Path
import json,math,heapq,collections
import numpy as np
P=Path('PCB');cs=json.loads((P/'manifests/pcb-layout-pads-v04.json').read_text(encoding='utf-8-sig'))['result'];pads=[];nets=collections.defaultdict(list)
for c in cs:
 for p in c['pads']:
  q={**p,'ref':c['ref'],'x':p['x']*.0254,'y':p['y']*.0254};shape=p['shape']
  if shape[0]=='POLYGON':
   v=[z for z in shape[1]if isinstance(z,(int,float))];q['hw']=max(abs(z*.0254-q['x'])for z in v[::2]);q['hh']=max(abs(z*.0254-q['y'])for z in v[1::2])
  else:
   ang=math.radians(p['rotation']);w=shape[1]*.0254;h=shape[2]*.0254;q['hw']=abs(w*math.cos(ang)/2)+abs(h*math.sin(ang)/2);q['hh']=abs(w*math.sin(ang)/2)+abs(h*math.cos(ang)/2)
  pads.append(q)
  if p['net']:nets[p['net']].append(q)
exclude={'GND','VIN_PROT','VIN_OR','VDD_3V3','VDD_4G','VDD_5V_IF'}
exclude.update(n for n in nets if 'USB'in n or 'RF'in n or 'ANT'in n or n.endswith('_SW'))
sel=[]
for n,ps in nets.items():
 if n in exclude or len(ps)<2:continue
 d=max(math.hypot(a['x']-b['x'],a['y']-b['y'])for a in ps for b in ps)
 if d<=7:sel.append((d,n,ps))
sel.sort();step=.08;nx=int(60/step)+1;ny=int(70/step)+1;xx,yy=np.meshgrid(np.arange(nx)*step,np.arange(ny)*step);routes=[];fails=[]

def gridpt(p):return(round(p['x']/step),round(p['y']/step))
def block(net,width):
 m=(xx<.4)|(xx>59.6)|(yy<.4)|(yy>69.6);margin=.17+width/2
 for p in pads:
  if p['net']==net:continue
  m|=(np.abs(xx-p['x'])<=p['hw']+margin)&(np.abs(yy-p['y'])<=p['hh']+margin)
 for r in routes:
  if r['net']==net:continue
  margin=.17+(width+r['widthMm'])/2
  for a,b in zip(r['pointsMm'],r['pointsMm'][1:]):
   x0,y0=a;x1,y1=b;den=(x1-x0)**2+(y1-y0)**2;t=np.clip(((xx-x0)*(x1-x0)+(yy-y0)*(y1-y0))/den,0,1);m|=((xx-(x0+t*(x1-x0)))**2+(yy-(y0+t*(y1-y0)))**2)<=margin**2
 return m

def astar(s,t,m):
 if m[s[1],s[0]]or m[t[1],t[0]]:return None
 q=[(math.hypot(s[0]-t[0],s[1]-t[1]),0,s)];prev={};dist={s:0};lim=0
 while q:
  _,g,u=heapq.heappop(q)
  if g!=dist[u]:continue
  if u==t:
   out=[u]
   while u!=s:u=prev[u];out.append(u)
   return out[::-1]
  lim+=1
  if lim>150000:return None
  for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
   v=(u[0]+dx,u[1]+dy)
   if not (0<v[0]<nx-1 and 0<v[1]<ny-1)or m[v[1],v[0]]:continue
   if dx and dy and(m[u[1],v[0]]or m[v[1],u[0]]):continue
   gg=g+(1.41421356237 if dx and dy else 1)
   if gg<dist.get(v,1e99):dist[v]=gg;prev[v]=u;heapq.heappush(q,(gg+math.hypot(v[0]-t[0],v[1]-t[1]),gg,v))
 return None
for _,n,ps in sel:
 width=.2032;connected=[ps[0]];rest=ps[1:]
 while rest:
  _,i,j=min((math.hypot(a['x']-b['x'],a['y']-b['y']),i,j)for i,a in enumerate(connected)for j,b in enumerate(rest));a=connected[i];b=rest[j];m=block(n,width);path=astar(gridpt(a),gridpt(b),m)
  if path is None:fails.append({'net':n,'from':a['ref']+':'+a['number'],'to':b['ref']+':'+b['number']});connected.append(rest.pop(j));continue
  points=[[a['x'],a['y']]];last=None
  for k in range(1,len(path)):
   dr=(path[k][0]-path[k-1][0],path[k][1]-path[k-1][1])
   if last is not None and dr!=last:points.append([path[k-1][0]*step,path[k-1][1]*step])
   last=dr
  points.extend([[path[-1][0]*step,path[-1][1]*step],[b['x'],b['y']]])
  points=[p for k,p in enumerate(points)if k==0 or math.hypot(p[0]-points[k-1][0],p[1]-points[k-1][1])>1e-6]
  routes.append({'net':n,'from':a['ref']+':'+a['number'],'to':b['ref']+':'+b['number'],'widthMm':width,'pointsMm':points});connected.append(rest.pop(j))
plan={'phase':'local low speed routing, RF USB and power excluded','gridMm':step,'clearanceMm':.17,'routes':routes,'failed':fails};(P/'manifests/pcb-local-route-plan-v04.json').write_text(json.dumps(plan,indent=2));print('planned',len(routes),'nets',len(set(r['net']for r in routes)),'failed',len(fails));print('nets',[r['net']for r in routes])
guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");'
for i in range(0,len(routes),12):
 rs=[]
 for r in routes[i:i+12]:
  a=r['pointsMm'];poly=[a[0][0]/.0254,a[0][1]/.0254,'L'];poly.extend(v/.0254 for p in a[1:]for v in p);rs.append({'net':r['net'],'width':r['widthMm']/.0254,'poly':poly})
 code=guard+'const Layer={TOP:1};const specs='+json.dumps(rs)+';const out=[];for(const z of specs){const polygon=eda.pcb_MathPolygon.createPolygon(z.poly);const p=await eda.pcb_PrimitivePolyline.create(z.net,Layer.TOP,polygon,z.width,true);if(!p)throw Error("Route failed "+z.net);out.push({net:z.net,id:p.getState_PrimitiveId()});}return {created:out,saved:await eda.pcb_Document.save()};'
 (P/f'scripts/route-local-v04-{i//12+1}.js').write_text(code)

