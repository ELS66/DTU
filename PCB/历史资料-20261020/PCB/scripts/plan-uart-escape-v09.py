from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text().replace('pcb-pads-power-v07.json','pcb-pads-final-v09.json').replace('routing-power-v07.json','routing-uart-preview-v09.json'))
step=.05;nx=1201;ny=1401;src=Path('PCB/scripts/plan-signals-v07.py').read_text();exec(src[src.index('def maskgeom'):src.index('def route3d')].replace('m[5:696,5:596]=False','m[int(.4/step):int(69.6/step),int(.4/step):int(59.6/step)]=False'))
new=[];newvia=[];lengths={}
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

holes=unary_union([Point(q['x'],q['y']).buffer(q['radius']) for q in json.loads((P/'manifests/mechanical-holes-v07.json').read_text())]);original=obstacles
def obstacles(net,layer):return unary_union([original(net,layer),holes])

failed=[]
uart=[('MCU_LTE_RX',(5.12318,47.9171),(3.5,47.45)),('MCU_LTE_TX',(5.12318,49.1871),(3.5,48.25))]
for net,a,b in uart:
 vias.append({'net':net,'x':b[0],'y':b[1],'diameter':.6})
 tracks.append({'net':net,'layer':1,'geom':LineString([a,b]).buffer(.0762)})
via={'net':'MCU_LTE_PWRKEY','x':3.55,'y':45.5,'diameter':.6};vias.append(via)
raw=json.loads((P/'manifests/uart-escape-removal-v09.json').read_text())['oldBottom']['polygon'];nums=[v for v in raw if isinstance(v,(int,float))];pts=[(x*.0254,y*.0254) for x,y in zip(nums[::2],nums[1::2])]
try:
 trace('MCU_LTE_PWRKEY',(3.55,45.5),pts[2],2,.1524,'UART-escape-control')
 new[-1]['pointsMm']+=pts[3:]
except Exception as e:failed.append(str(e));print(str(e))
try:trace('MCU_LTE_PWRKEY',(5.12318,46.6471),(3.55,45.5),1,.1524,'UART-escape-control')
except Exception as e:failed.append(str(e));print(str(e))
for net,a,b in uart:
 obs=obstacles(net,1)
 if LineString([a,b]).buffer(.0762+.1524).intersects(obs):failed.append('UART escape trace '+net)
 if Point(*b).buffer(.3+.1524).intersects(unary_union([obstacles(net,l) for l in [1,2,16]])):failed.append('UART escape via '+net)
 new.append({'net':net,'layer':1,'widthMm':.1524,'pointsMm':[a,b],'role':'UART-source-fanout'})
print('failed',failed)
(P/'manifests/uart-escape-plan-v09.json').write_text(json.dumps({'routes':new,'via':via,'uart':uart,'failed':failed},indent=2))
