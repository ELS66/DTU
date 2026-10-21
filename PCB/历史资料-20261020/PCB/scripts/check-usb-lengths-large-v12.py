from pathlib import Path
exec(Path('PCB/scripts/router-large-v12.py').read_text())
plan=json.load(open(P/'manifests/critical-large-v12.json'));rows=[]
def length(net,r,pin,j,endpin=None):
 rs=[r for r in plan['routes'] if r['net']==net];vs=[v for v in plan['vias'] if v['net']==net];ps=[p for p in pads if p['net']==net];pts={};edges=[]
 for rr in rs:
  for aa,bb in zip(rr['pointsMm'],rr['pointsMm'][1:]):
   edges.append((rr['layer'],LineString([aa,bb]),aa,bb));pts.setdefault(rr['layer'],[]).extend([aa,bb])
 for k in [1,2,16]:
  pts.setdefault(k,[]).extend([(v['x'],v['y']) for v in vs]);pts[k].extend([(p['x'],p['y']) for p in ps if p['layer'] in [k,12]])
 nodes=[];indexes={}
 def node(k,pt):
  key=(k,round(pt[0],5),round(pt[1],5))
  if key not in indexes:indexes[key]=len(nodes);nodes.append(key)
  return indexes[key]
 adj=collections.defaultdict(list)
 def edge(a,b,w):adj[a].append((b,w));adj[b].append((a,w))
 for k,g,a,b in edges:
  near=sorted([(g.project(Point(pt)),pt) for pt in pts[k] if Point(pt).distance(g)<.00002],key=lambda x:x[0])
  for (da,a),(db,b) in zip(near,near[1:]):edge(node(k,a),node(k,b),db-da)
 for v in vs:
  for k in [2,16]:edge(node(1,(v['x'],v['y'])),node(k,(v['x'],v['y'])),0)
 for p in ps:
  ks=[1,2,16] if p['layer']==12 else [p['layer']]
  for k in ks:
   c=node(k,(p['x'],p['y']))
   for pt in pts[k]:
    if p['geom'].covers(Point(pt)):edge(c,node(k,pt),math.dist((p['x'],p['y']),pt))
  if p['layer']==12:
   for k in [2,16]:edge(node(1,(p['x'],p['y'])),node(k,(p['x'],p['y'])),0)
 a=next(p for p in ps if p['ref']==r and p['number']==pin);b=next(p for p in ps if p['ref']==j and (p['number']==endpin if endpin else p['number'] in ['2','3']));s=node(1 if a['layer']==12 else a['layer'],(a['x'],a['y']));t=node(1 if b['layer']==12 else b['layer'],(b['x'],b['y']));q=[(0,s)];dist={s:0}
 while q:
  d,u=heapq.heappop(q)
  if d!=dist[u]:continue
  if u==t:return d
  for v,w in adj[u]:
   if d+w<dist.get(v,1e100):dist[v]=d+w;heapq.heappush(q,(d+w,v))
 raise Exception('No USB path '+net)
for fam,refs,j in [('ESP',['R15','R16'],'J6'),('LTE',['R60','R61'],'J7')]:
 vals=[];srcs=[]
 for side,res,pn in zip(['DP','DM'],refs,['14','13'] if fam=='ESP' else ['59','60']):
  d=length(f'{fam}_USB_{side}_EXT',res,'2',j);src=length(f'{fam}_USB_{side}','U1' if fam=='ESP' else 'U2',pn,res,'1')
  vals.append(d);srcs.append(src);print(fam,side,round(d+src,4))
 rows.append({'family':fam,'seriesToHeaderMm':vals,'moduleToSeriesMm':srcs,'copperLengthMm':[a+b for a,b in zip(vals,srcs)],'skewMm':abs(vals[0]+srcs[0]-vals[1]-srcs[1])})
(P/'reports/USB长度核对-V0.12.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
