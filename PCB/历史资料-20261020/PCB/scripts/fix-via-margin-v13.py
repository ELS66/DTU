from pathlib import Path
exec(Path('PCB/scripts/router-v13.py').read_text(encoding='utf8'))
plan=json.load(open(P/'manifests/connected-routing-v13.json',encoding='utf8'));v=plan['vias'][190];old=(v['x'],v['y']);others=[]
for p in pads:
 if p['net']!=v['net']:others.append((p['geom'],{1,2,15,16} if p['layer']==12 else {p['layer']}))
for r in plan['routes']:
 if r['net']!=v['net']:others.append((LineString(r['pointsMm']).buffer(r['widthMm']/2),{r['layer']}))
for q in plan['vias']:
 if q['net']!=v['net']:others.append((Point(q['x'],q['y']).buffer(q['diameter']/2),{1,2,15,16}))
attached=[r for r in plan['routes'] if r['net']==v['net'] and any(math.dist(pt,old)<.0001 for pt in r['pointsMm'])]
opts=sorted([(i*i+j*j,old[0]+i*.025,old[1]+j*.025) for i in range(-8,9) for j in range(-8,9)])
for _,x,y in opts:
 vg=Point(x,y).buffer(v['diameter']/2)
 if any(vg.distance(g)<.155 for g,ls in others):continue
 changed=[];bad=False
 for r in attached:
  pts=[(x,y) if math.dist(pt,old)<.0001 else pt for pt in r['pointsMm']];g=LineString(pts).buffer(r['widthMm']/2)
  if any(r['layer'] in ls and g.distance(o)<.1528 for o,ls in others):bad=True;break
  changed.append((r,pts))
 if bad:continue
 print('Via shift',old,(x,y));v['x']=x;v['y']=y
 for r,pts in changed:r['pointsMm']=pts
 break
else:raise Exception('No safe micro adjustment')
new[:]=plan['routes'];newvias[:]=plan['vias'];save_plan('connected-routing-v13',[])
