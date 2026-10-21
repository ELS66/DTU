"""Review actual library body outlines, separately from electrical pad clearance."""
import sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path('PCB/.tools').resolve()))
from shapely.geometry import Polygon,Point,box
from shapely.ops import unary_union
from shapely.affinity import rotate,translate,scale
P=Path('PCB');M=P/'manifests'
cs=json.loads((M/'hy20-final-pcb-pads-v13.json').read_text(encoding='utf8'))['result']
lib=json.loads((M/'footprint-geometries-v13.json').read_text(encoding='utf8'))
s=json.loads((M/'hy20-footprint-smd-layer-v13.json').read_text(encoding='utf8'))['result']['source']
lib['0190edb3deceabcd']=[]
for l in s.splitlines():
 if '||' in l:
  h,b=l.split('||',1);lib['0190edb3deceabcd'].append({**json.loads(h),**json.loads(b.removesuffix('|'))})
def pathgeom(path):
 if path and isinstance(path[0],list):return unary_union([pathgeom(q) for q in path])
 if path and path[0]=='CIRCLE':return Point(path[1]*.0254,path[2]*.0254).buffer(path[3]*.0254)
 if any(isinstance(v,str) and v!='L' for v in path):return Polygon()
 v=[v*.0254 for v in path if isinstance(v,(int,float))]
 return Polygon(list(zip(v[::2],v[1::2]))).buffer(0) if len(v)>=6 else Polygon()
bodies=[];missing=[]
for c in cs:
 parts=[pathgeom(r['path']) for r in lib.get(c['footprint']['uuid'],[]) if r.get('layerId')==48 and 'path' in r]
 g=unary_union(parts)
 if g.is_empty: missing.append(c['ref']);continue
 g=translate(rotate(g,c['rotation'],origin=(0,0)),c['x']*.0254,c['y']*.0254)
 bodies.append({'ref':c['ref'],'geom':g,'bounds':list(g.bounds)})
overlap=[];tight=[];enlarged=[]
for i,a in enumerate(bodies):
 if a['ref'] in ['C50','C51','R32','J6','J7']:continue
 for b in bodies[:i]:
  if b['ref'] in ['C50','C51','R32','J6','J7']:continue
  g,h=a['geom'],b['geom'];area=g.intersection(h).area;gap=g.distance(h)
  item={'refs':[a['ref'],b['ref']],'bodyGapMm':gap,'overlapAreaMm2':area}
  if area>.0001:overlap.append(item)
  elif gap<.3:tight.append(item)
  if scale(g,xfact=1.05,yfact=1.05,origin='center').intersection(scale(h,xfact=1.05,yfact=1.05,origin='center')).area>.0001:enlarged.append(item)
result={'scope':'library layer48 body geometry; excludes DNP; does not replace manufacturer drawings or DFM 3D model engine','bodyCount':len(bodies),'missingBodyOutline':missing,'bodyOverlaps':overlap,'bodyGapBelow0_3mm':tight,'uniform5PercentExpansionIntersections':enlarged,'bounds':[{k:v for k,v in r.items() if k!='geom'} for r in bodies]}
(M/'smt-body-audit-v13.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k!='bounds'},ensure_ascii=True,indent=2))
