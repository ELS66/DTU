from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text().replace('pcb-pads-power-v07.json','pcb-pads-usb-v07.json').replace('routing-power-v07.json','routing-usb-priority-v07.json'))
step=.1;nx=601;ny=701;src=Path('PCB/scripts/plan-signals-v07.py').read_text();exec(src[src.index('def maskgeom'):src.index('def route3d')]);plans=[]
def path(a,b,obs,margin):
 m=maskgeom(obs,margin);s=tuple(round(v/step) for v in a);t=tuple(round(v/step) for v in b)
 if m[s[1],s[0]] or m[t[1],t[0]]:return None
 hp=[(math.dist(s,t),0,s)];ds={s:0};prev={}
 while hp:
  _,g,u=heapq.heappop(hp)
  if g!=ds[u]:continue
  if u==t:
   seq=[u]
   while u!=s:u=prev[u];seq.append(u)
   pts=[(x*step,y*step) for x,y in seq[::-1]];out=[a];i=0
   while i<len(pts)-1:
    for j in range(min(i+100,len(pts)-1),i,-1):
     if not LineString([out[-1],pts[j]]).buffer(margin-.018).intersects(obs):break
    out.append(pts[j]);i=j
   out.append(b);return LineString(out).simplify(.02)
  x,y=u
  for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
   xx,yy=x+dx,y+dy
   if not(0<xx<nx-1 and 0<yy<ny-1) or m[yy,xx]:continue
   if dx and dy and (m[y,xx] or m[yy,x]):continue
   v=(xx,yy);gg=g+(1.41421356 if dx and dy else 1)
   if gg<ds.get(v,1e30):ds[v]=gg;prev[v]=u;heapq.heappush(hp,(gg+math.dist(v,t),gg,v))
 return None
for label,nets,layer,ends in [('LTE',['LTE_USB_DP_EXT','LTE_USB_DM_EXT'],1,[(54.4,35.4),(39.9,68.6)]),('ESP',['ESP_USB_DP_EXT','ESP_USB_DM_EXT'],2,[(1.2,43),(11.5,63.4)])]:
 obs=unary_union([p['geom'] for p in pads if p['net'] not in nets and p['layer'] in [layer,12]]+[t['geom'] for t in tracks if t['net'] not in nets and t['layer']==layer]+[Point(v['x'],v['y']).buffer(v['diameter']/2) for v in vias if v['net'] not in nets]+[Point(h['x'],h['y']).buffer(h['radius']) for h in json.loads((P/'manifests/mechanical-holes-v07.json').read_text())]);center=path(*ends,obs,.51)
 if center is None:print(label,'NO CORE PATH');continue
 ls=center.offset_curve(.2,join_style=2);rs=center.offset_curve(-.2,join_style=2)
 if ls.geom_type!='LineString' or rs.geom_type!='LineString':print(label,'bad offset');continue
 dist=ls.distance(rs);clear=[g.buffer(.12+.1524).intersects(obs) for g in [ls,rs]];print(label,'CORE',round(center.length,3),'pair gap',round(dist-.24,3),'clear',clear,'vertices',len(center.coords))
 if dist<.3924 or any(clear):continue
 plans.append({'label':label,'nets':nets,'layer':layer,'centerlineMm':list(center.coords),'tracksMm':[list(ls.coords),list(rs.coords)],'lengthsMm':[ls.length,rs.length],'widthMm':.24,'gapMm':.16})
(P/'manifests/usb-pair-core-v07.json').write_text(json.dumps(plans,indent=2))


