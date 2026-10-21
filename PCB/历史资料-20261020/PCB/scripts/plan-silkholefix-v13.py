from pathlib import Path
import json,zipfile
exec(Path('PCB/scripts/render-hy20-gerber-v13.py').read_text().split('for label,copper,mask,silk in')[0])
from shapely.affinity import translate
z.close();z=zipfile.ZipFile('PCB/eda/DTU-V0.13-60x70-Silkclean-Gerber.zip');cache.clear()
t=json.loads(Path('PCB/manifests/silkholefix-text-groups-v13.json').read_text())['texts'];parts={a['id']:[] for a in t}
for g,d in geom('Gerber_TopSilkscreenLayer.GTO')[0]:
 row=[a for a in t if (len(a['text'])==1)==(g.centroid.y<9.9)];a=min(row,key=lambda a:abs(g.centroid.x-a['x']*.0254));parts[a['id']].append(g)
G={a['id']:unary_union(parts[a['id']]) for a in t};mask=unary_union([g for g,d in geom('Gerber_TopSolderMaskLayer.GTS')[0] if d]);hole=unary_union([Point(x,y).buffer(di/2) for x,y,di in drill('Drill_PTH_Through.DRL')+drill('Drill_NPTH_Through.DRL')]);fixed=unary_union([G[a['id']] for a in t[5:]])
choices=[]
for dy in [i*.05 for i in range(15,27)]:
 pins=unary_union([translate(G[a['id']],0,dy) for a in t[:4]])
 if min(pins.distance(mask),pins.distance(hole),pins.distance(fixed))<.2:continue
 for dxn in [i*.1 for i in range(-16,17)]:
  for dyn in [i*.05 for i in range(12,31)]:
   name=translate(G[t[4]['id']],dxn,dyn)
   if min(name.distance(mask),name.distance(hole),name.distance(pins),name.distance(fixed))<.2:continue
   choices.append((dy+abs(dxn)+dyn,dy,dxn,dyn, min(pins.distance(hole),name.distance(hole)),min(pins.distance(mask),name.distance(mask))))
print('uniform alternatives',sorted(choices)[:10])
b=t[2];rest=unary_union([G[a['id']] for a in t if a!=b]);best=[]
for dx in [i*.025 for i in range(-40,41)]:
 for dy in [i*.025 for i in range(-40,41)]:
  q=translate(G[b['id']],dx,dy)
  if min(q.distance(mask),q.distance(hole),q.distance(rest))>=.2:best.append((abs(dx)+abs(dy)*1.5,dx,dy,q.distance(hole),q.distance(mask),q.distance(rest)))
print('B-only',sorted(best)[:10])
