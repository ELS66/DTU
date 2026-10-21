import sys,json,math,heapq,collections,time
from pathlib import Path
sys.path.insert(0,str(Path('PCB/.tools').resolve()))
import numpy as np
import shapely
from shapely.geometry import Point,LineString,Polygon,box
from shapely.ops import unary_union
P=Path('PCB');cs=json.loads((P/'manifests/pcb-pads-power-v07.json').read_text(encoding='utf-8-sig'))['result'];old=json.loads((P/'manifests/routing-power-v07.json').read_text(encoding='utf-8-sig'))['result'];pads=[];tracks=[];vias=[];routes=[];fail=[]
for c in cs:
 for q in c['pads']:
  r={**q,'ref':c['ref'],'x':q['x']*.0254,'y':q['y']*.0254}
  if q['shape'][0]=='POLYGON':
   v=[x for x in q['shape'][1] if isinstance(x,(int,float))];pts=list(zip([x*.0254 for x in v[::2]],[x*.0254 for x in v[1::2]]));w=max(x[0] for x in pts)-min(x[0] for x in pts);h=max(x[1] for x in pts)-min(x[1] for x in pts)
  else:
   w,h=[x*.0254 for x in q['shape'][1:3]];ang=math.radians(q['rotation']);pts=[]
   for dx,dy in [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]:pts.append((r['x']+dx*math.cos(ang)-dy*math.sin(ang),r['y']+dx*math.sin(ang)+dy*math.cos(ang)))
  r['geom']=Polygon(pts);r['w']=w;r['h']=h;pads.append(r)
for t in old['lines']:tracks.append({'net':t['net'],'layer':t['layer'],'geom':LineString([(t['x1']*.0254,t['y1']*.0254),(t['x2']*.0254,t['y2']*.0254)]).buffer(t['width']*.0254/2)})
for t in old['polys']:
 if t['layer'] not in [1,2,15,16]:continue
 a=t['polygon'];pts=[(a[0]*.0254,a[1]*.0254)];v=[x for x in a[3:] if isinstance(x,(int,float))];pts +=list(zip([x*.0254 for x in v[::2]],[x*.0254 for x in v[1::2]]));tracks.append({'net':t['net'],'layer':t['layer'],'geom':LineString(pts).buffer(t['width']*.0254/2)})
for v in old['vias']:vias.append({'net':v['net'],'x':v['x']*.0254,'y':v['y']*.0254,'diameter':v['diameter']*.0254,'existing':True})
def obstacles(net,layer):
 out=[q['geom'] for q in pads if q['net']!=net and (q['layer']==layer or q['layer']==12)]
 out+=[t['geom'] for t in tracks if t['net']!=net and t['layer']==layer]
 out+=[Point(v['x'],v['y']).buffer(v['diameter']/2) for v in vias if v['net']!=net]
 return unary_union(out)
