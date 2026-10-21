"""Offline via-aware reroute. Preserve placement, critical nets, and power copper."""
from pathlib import Path
src=Path('PCB/scripts/router-v13.py').read_text(encoding='utf8').replace('read-pcb-pads-v13.json','read-pcb-pads-before-opt-v13.json')
exec(src)
from shapely.strtree import STRtree
from shapely.ops import nearest_points
import argparse,copy
args=argparse.ArgumentParser();args.add_argument('--nets',nargs='*');args.add_argument('--resume',action='store_true');args=args.parse_args()
BASE=P/'manifests/routing-opt-baseline-v13.json'
OUT=P/'manifests/routing-optimized-v13.json'
plan=json.loads((OUT if args.resume and OUT.exists() else BASE).read_text())
baseline=json.loads(BASE.read_text())
log=json.loads((P/'manifests/routing-optimization-log-v13.json').read_text()) if args.resume else []
# Keep the enlarged production pad envelope even though the component getter reports library defaults.
for p in pads:
 if p['ref'] in ['D18','D20']:
  p['geom']=translate(rotate(box(-.125,-.15,.125,.15),p['rotation'],origin=(0,0)),p['x'],p['y'])

def objects(net,rs,vs):
 os=[]
 for p in pads:
  if p['net']==net:os.append({'geom':p['geom'],'ls':set(layers) if p['layer']==12 else {p['layer']},'pts':[(p['x'],p['y'],p['layer'])],'pad':True})
 for v in vs:
  if v['net']==net:os.append({'geom':Point(v['x'],v['y']).buffer(v['diameter']/2),'ls':set(layers),'pts':[(v['x'],v['y'],l) for l in layers]})
 for r in rs:
  if r['net']==net:os.append({'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2),'ls':{r['layer']},'pts':[(x,y,r['layer']) for x,y in r['pointsMm']]})
 return os

def groups(net,rs,vs):
 os=objects(net,rs,vs);parent=list(range(len(os)))
 def find(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 tr=STRtree([o['geom'] for o in os])
 for i,a in enumerate(os):
  for j in tr.query(a['geom'].buffer(.001)):
   if j<i and a['ls']&os[j]['ls'] and a['geom'].distance(os[j]['geom'])<.001:parent[find(i)]=find(j)
 gs={}
 for i,o in enumerate(os):gs.setdefault(find(i),[]).append(o)
 return list(gs.values())

def pathfind(net,a,b,width,allowed=(1,2,16),limit=90000):
 obs=[obstacles(net,k) for k in allowed]
 masks=[maskgeom(o,width/2+.159) for o in obs]
 allobs=unary_union([obstacles(net,k) for k in layers]+[p['geom'].buffer(.04) for p in pads if p['net']==net]+[Point(v['x'],v['y']).buffer(v['diameter']/2) for v in vias])
 vm=maskgeom(allobs,.225+.163)
 for v in vias:
  if v['net']==net:vm[round(v['y']/step),round(v['x']/step)]=False
 def seeds(p):
  ls=range(len(allowed)) if p[2]==12 else [allowed.index(p[2])] if p[2] in allowed else []
  opts=[];cx,cy=round(p[0]/step),round(p[1]/step)
  for l in ls:
   for x in range(cx-3,cx+4):
    for y in range(cy-3,cy+4):
     if not(0<x<nx-1 and 0<y<ny-1) or masks[l][y,x]:continue
     q=(x*step,y*step);d=math.dist(p[:2],q)
     if d<.28 and LineString([p[:2],q]).distance(obs[l])>width/2+.154:opts.append((d,(x,y,l)))
  return sorted(opts)
 ss,tt=seeds(a),seeds(b)
 if not ss or not tt:return None
 target={p:d/step for d,p in tt};cx,cy=b[0]/step,b[1]/step;targetls={p[2] for _,p in tt}
 # A layer transition costs the equivalent of 25 mm of trace. Prefer fewer holes.
 via_cost=150
 def h(u):
  dx,dy=abs(u[0]-cx),abs(u[1]-cy)
  return max(dx,dy)+(math.sqrt(2)-1)*min(dx,dy)+(0 if u[2] in targetls else via_cost)
 hp=[(d/step+1.6*h(s),d/step,s) for d,s in ss];heapq.heapify(hp);ds={s:d/step for d,s in ss};prev={};count=0
 while hp:
  _,cost,u=heapq.heappop(hp)
  if cost>ds.get(u,1e50)+1e-8:continue
  if u in target:
   seq=[u]
   while u in prev:u=prev[u];seq.append(u)
   seq.reverse();chunks=[];pts=[list(a[:2]),[seq[0][0]*step,seq[0][1]*step]];l=seq[0][2];last=None;vs=[]
   for u,v in zip(seq,seq[1:]):
    if u[2]!=v[2]:
     pt=[u[0]*step,u[1]*step];pts.append(pt);chunks.append((l,pts));pts=[pt];l=v[2];last=None;vs.append(pt)
    else:
     direction=(v[0]-u[0],v[1]-u[1])
     if last is not None and direction!=last:pts.append([u[0]*step,u[1]*step])
     last=direction
   pts.extend([[seq[-1][0]*step,seq[-1][1]*step],list(b[:2])]);chunks.append((l,pts));out=[]
   for l,pts in chunks:
    pts=[p for i,p in enumerate(pts) if i==0 or math.dist(p,pts[i-1])>1e-7]
    if len(pts)<2:continue
    # Remove grid staircases by clear line-of-sight shortcuts. No clearance relaxation.
    simple=[pts[0]];i=0
    while i<len(pts)-1:
     j=len(pts)-1
     while j>i+1 and LineString([pts[i],pts[j]]).distance(obs[l])<width/2+.157:j-=1
     simple.append(pts[j]);i=j
    geom=LineString(simple)
    if geom.distance(obs[l])<width/2+.153:return None
    out.append({'net':net,'layer':allowed[l],'widthMm':width,'pointsMm':simple})
   return out,vs
  count+=1
  if count>limit:return None
  x,y,l=u;opts=[]
  for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
   xx,yy=x+dx,y+dy
   if not(0<xx<nx-1 and 0<yy<ny-1) or masks[l][yy,xx]:continue
   if dx and dy and (masks[l][y,xx] or masks[l][yy,x]):continue
   opts.append(((xx,yy,l),math.sqrt(2) if dx and dy else 1))
  if len(allowed)>1 and not vm[y,x]:
   for ll in range(len(allowed)):
    if ll!=l and not masks[ll][y,x]:opts.append(((x,y,ll),via_cost))
  for v,w in opts:
   g=cost+w
   if g+1e-8<ds.get(v,1e50):ds[v]=g;prev[v]=u;heapq.heappush(hp,(g+1.6*h(v),g,v))
 return None

def length(rs):return sum(LineString(r['pointsMm']).length for r in rs)

def reroute(net):
 global tracks,vias
 oldrs=[r for r in plan['routes'] if r['net']==net];oldvs=[v for v in plan['vias'] if v['net']==net]
 tracks=[{'net':r['net'],'layer':r['layer'],'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2),'points':r['pointsMm']} for r in plan['routes'] if r['net']!=net]
 vias=[v for v in plan['vias'] if v['net']!=net]
 rs=[];vs=[];width=min(r['widthMm'] for r in oldrs)
 # Never narrow any signal below its existing minimum width.
 width=max(width,.1524)
 gs=groups(net,rs,vs);attempt=0
 while len(gs)>1:
  choices=[]
  for i,a in enumerate(gs):
   for j in range(i):
    b=gs[j]
    ap=list(dict.fromkeys(p for o in a for p in o['pts']));bp=list(dict.fromkeys(p for o in b for p in o['pts']))
    for pa in ap:
     pb=min(bp,key=lambda z:math.dist(pa[:2],z[:2]));choices.append((math.dist(pa[:2],pb[:2]),i,j,pa,pb))
  success=False
  for dist,i,j,a,b in sorted(choices)[:3]:
   same=[l for l in layers if a[2] in [12,l] and b[2] in [12,l]]
   rout=None
   for l in same:
    if LineString([a[:2],b[:2]]).distance(obstacles(net,l))>width/2+.158:rout=([{'net':net,'layer':l,'widthMm':width,'pointsMm':[list(a[:2]),list(b[:2])]}],[]);break
   if rout is None:rout=pathfind(net,a,b,width)
   if rout is None:continue
   r,v=rout
   for z in r:rs.append(z);tracks.append({'net':net,'layer':z['layer'],'geom':LineString(z['pointsMm']).buffer(width/2),'points':z['pointsMm']})
   for x,y in v:
    if any(q['net']==net and math.dist((x,y),(q['x'],q['y']))<.04 for q in vias):continue
    if any(q['net']==net and q['layer']==12 and q['geom'].covers(Point(x,y)) for q in pads):continue
    z={'net':net,'x':x,'y':y,'diameter':.45,'hole':.2};vs.append(z);vias.append(z)
   success=True;break
  attempt+=1
  if not success or attempt>20:return {'net':net,'accepted':False,'reason':'routing failed','oldVias':len(oldvs)}
  after=groups(net,rs,vs)
  if len(after)>=len(gs):return {'net':net,'accepted':False,'reason':'no connectivity progress','oldVias':len(oldvs)}
  gs=after
 oldlen=length(oldrs);newlen=length(rs)
 accept=len(vs)<len(oldvs) and newlen<=oldlen*1.10+2
 record={'net':net,'accepted':accept,'oldVias':len(oldvs),'newVias':len(vs),'oldLengthMm':round(oldlen,3),'newLengthMm':round(newlen,3),'groups':len(gs)}
 if accept:
  plan['routes']=[r for r in plan['routes'] if r['net']!=net]+rs
  plan['vias']=[v for v in plan['vias'] if v['net']!=net]+vs
 return record

protected={'GND','VDD_3V3','VDD_4G','VIN_IN','VIN_DIODE','VIN_PROT','SIM_VDD','LTE_VDD_EXT','LTE_SW','LTE_BST','LTE_FB','MCU_LDO_FB','LTE_ANT','LTE_RF_FEED'}
counts=collections.Counter(v['net'] for v in plan['vias'])
nets=args.nets or sorted([n for n in counts if n not in protected and 'USB' not in n and not n.startswith('232_C') and n!='232_VMINUS'],key=lambda n:(-counts[n],n))
for net in nets:
 t=time.time();print('START',net,flush=True);record=reroute(net);record['seconds']=round(time.time()-t,1);log.append(record);print(json.dumps(record),flush=True)
 OUT.write_text(json.dumps(plan,indent=2));(P/'manifests/routing-optimization-log-v13.json').write_text(json.dumps(log,indent=2))
print('RESULT vias',len(baseline['vias']),'->',len(plan['vias']),'routes',len(plan['routes']),flush=True)

