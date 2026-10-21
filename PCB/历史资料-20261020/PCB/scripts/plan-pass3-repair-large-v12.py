from pathlib import Path
exec(Path('PCB/scripts/plan-pass3-fanout-large-v12.py').read_text(encoding='utf-8-sig'))
step=.1;nx=601;ny=701
def softescape(net,p):
 protected_tracks=[t['geom'] for t in tracks if t['net']!=net and (t['net'] in protected or not t.get('id')) and t['layer']==p['layer']]
 hard=unary_union([q['geom'] for q in pads if q['net']!=net and q['layer'] in [12,p['layer']]]+holes+[Point(v['x'],v['y']).buffer(v['diameter']/2) for v in vias if v['net']!=net]+protected_tracks)
 m=maskgeom(hard,.0762+.16)
 hardvia=unary_union([q['geom'] for q in pads]+holes+[Point(v['x'],v['y']).buffer(max(v['diameter']/2,(v['hole']+.2)/2+.3-.153)) for v in vias]+[t['geom'] for t in tracks if t['net']!=net and (t['net'] in protected or not t.get('id'))])
 vm=maskgeom(hardvia,.225+.16)
 soft=unary_union([t['geom'] for t in tracks if t['net']!=net and t.get('id') and t['net'] not in protected and t['layer']==p['layer']]);sm=maskgeom(soft,.0762+.16)
 cx,cy=round(p['x']/step),round(p['y']/step);hp=[];dist={};prev={}
 for x in range(cx-3,cx+4):
  for y in range(cy-3,cy+4):
   if m[y,x] or LineString([(p['x'],p['y']),(x*step,y*step)]).distance(hard)<.0762+.153:continue
   cost=math.dist((p['x'],p['y']),(x*step,y*step));dist[x,y]=cost;heapq.heappush(hp,(cost,(x,y)))
 while hp:
  cost,u=heapq.heappop(hp)
  if cost!=dist[u]:continue
  x,y=u
  if not vm[y,x]:
   seq=[u]
   while seq[-1] in prev:seq.append(prev[seq[-1]])
   seq.reverse();pts=[(p['x'],p['y'])]+[(a*step,b*step) for a,b in seq];line=LineString(pts);pt=Point(x*step,y*step)
   blockers=[t for t in tracks if t['net']!=net and ((t['layer']==p['layer'] and line.distance(t['geom'])<.0762+.16) or pt.distance(t['geom'])<.225+.16)]
   if len(blockers)<=4 and all(t.get('id') and t['net'] not in protected for t in blockers):
    for t in blockers:removed[t['id']]=t['net'];tracks.remove(t)
    # Compact equal-direction grid segments.
    clean=[pts[0]]
    for i in range(1,len(pts)-1):
     aa=np.array(pts[i])-pts[i-1];bb=np.array(pts[i+1])-pts[i]
     if abs(aa[0]*bb[1]-aa[1]*bb[0])>1e-8:clean.append(pts[i])
    clean.append(pts[-1]);assert addline(net,p['layer'],clean)
    v={'net':net,'x':x*step,'y':y*step,'diameter':.45,'hole':.2};vias.append(v);newvias.append(v)
    escaped.append({'net':net,'ref':p['ref'],'pin':p['number'],'x':v['x'],'y':v['y'],'removed':[t['id'] for t in blockers]});print('SOFT ESCAPE',escaped[-1],flush=True);return True
  for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
   xx,yy=x+dx,y+dy
   if not(0<xx<nx-1 and 0<yy<ny-1) or abs(xx-cx)>60 or abs(yy-cy)>60 or m[yy,xx] or (dx and dy and (m[y,xx] or m[yy,x])):continue
   d=cost+(math.sqrt(2) if dx and dy else 1)+(50 if sm[yy,xx] else 0)
   if d<dist.get((xx,yy),1e100):dist[xx,yy]=d;prev[xx,yy]=u;heapq.heappush(hp,(d,(xx,yy)))
 return False
for net,ref,pin in [('LED_LTE_R_N','U1','9')]:
 p=next(p for p in pads if p['ref']==ref and p['number']==pin);assert softescape(net,p),(net,ref,pin)
save_plan('pass3-fanout-large-v12')
(P/'manifests/pass3-ripup-large-v12.json').write_text(json.dumps({'removed':removed,'escaped':escaped},indent=2),encoding='utf-8')
# Repair original signals and the few ordinary traces moved out of their way.
layers=[1,2,15,16]
baseobs=obstacles
def obstacles(net,layer,ignore=()):
 g=baseobs(net,layer,ignore)
 if layer==15 and net!='GND':
  g=unary_union([g,box(16.4,54.8,24,61.5),box(27.3,38,35,43.4),box(27.8,42.5,29.6,60.2),box(28,58.8,42.7,64.7),box(17.8,60.2,20,65),box(6.5,58,14.5,65.5)])
 return g
new=[];newvias=[];failed=[]
for net in list(dict.fromkeys(nets+list(removed.values()))):
 gs=groups(net)
 while len(gs)>1:
  choices=sorted((math.dist(a[:2],b[:2]),i,j,a,b) for i,g in enumerate(gs) for j,h in enumerate(gs[:i]) for a in g for b in h)
  success=False
  # First route existing escapes; inner 1 is used only when surface/inner 2 cannot pass.
  seenpairs=set()
  for _,i,j,a,b in choices:
   key=(tuple(round(z,3) for z in a),tuple(round(z,3) for z in b))
   if key in seenpairs:continue
   seenpairs.add(key)
   if len(seenpairs)>8:break
   if a[2]==b[2] and addline(net,a[2],[a[:2],b[:2]]):success=True
   else:
    for allowed in [(1,2,16),(1,2,15,16)]:
     result=route(net,a,b,.1524,allowed,limit=240000)
     if result is None:continue
     rr,vv=result
     for r in rr:new.append(r);tracks.append({'net':net,'layer':r['layer'],'points':r['pointsMm'],'geom':LineString(r['pointsMm']).buffer(.0762)})
     for x,y in vv:
      if not any(v['net']==net and Point(x,y).distance(Point(v['x'],v['y']))<.12 for v in vias):
       v={'net':net,'x':x,'y':y,'diameter':.45,'hole':.2};vias.append(v);newvias.append(v)
     success=True;break
   if success:gs[j].extend(gs[i]);gs.pop(i);break
  if not success:failed.append({'net':net,'groupsRemaining':len(gs),'representatives':[g[0] for g in gs]});break
 print('REPAIR',net,'groups',len(gs),'routes',len(new),'vias',len(newvias),flush=True)
 save_plan('pass3-repair-large-v12',failed)
# Correct inner-layer selection in generated native scripts.
for f in P.glob('scripts/apply-pass3-repair-large-v12-*.js'):
 f.write_text(f.read_text(encoding='utf-8').replace("const layer=z.layer===1?EPCB_LayerId.TOP:z.layer===2?EPCB_LayerId.BOTTOM:EPCB_LayerId.INNER_2;","const layer=z.layer;"),encoding='utf-8')
