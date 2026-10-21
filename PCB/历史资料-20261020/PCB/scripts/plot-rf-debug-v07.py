exec(open('PCB/scripts/debug-rf-endpoint-v07.py',encoding='utf-8-sig').read())
m=maskgeom(geom,.33)
for endpoint in [a,b]:
 s=(round(endpoint[0]/step),round(endpoint[1]/step));todo=collections.deque([s]);seen={s}
 while todo:
  x,y=todo.popleft()
  for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
   v=x+dx,y+dy
   if v not in seen and 0<v[0]<nx-1 and 0<v[1]<ny-1 and not m[v[1],v[0]]:seen.add(v);todo.append(v)
 print('reachable',endpoint,len(seen),[min(x for x,y in seen)*step,min(y for x,y in seen)*step,max(x for x,y in seen)*step,max(y for x,y in seen)*step])
from PIL import Image,ImageDraw
im=Image.new('RGB',(900,700),'white');d=ImageDraw.Draw(im);x0,y0=44,44;scale=60
for p in pads:
 if p['geom'].bounds[0]>59 or p['geom'].bounds[2]<44 or p['geom'].bounds[1]>54 or p['geom'].bounds[3]<44:continue
 d.polygon([((x-x0)*scale,(54-y)*scale) for x,y in p['geom'].exterior.coords],fill='green' if p['net']=='GND' else 'red');d.text(((p['x']-x0)*scale,(54-p['y'])*scale),p['ref']+':'+p['number'],fill='black')
for t in tracks:
 if t['layer']!=1:continue
 for g in list(t['geom'].geoms) if hasattr(t['geom'],'geoms') else [t['geom']]:
  d.polygon([((x-x0)*scale,(54-y)*scale) for x,y in g.exterior.coords],fill='green' if t['net']=='GND' else 'orange')
im.save('PCB/reports/rf-routing-debug-v07.png')
