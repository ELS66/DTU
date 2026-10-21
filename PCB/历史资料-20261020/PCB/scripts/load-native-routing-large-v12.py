from pathlib import Path
exec(Path('PCB/scripts/router-large-v12.py').read_text(encoding='utf8'))
step=.1;nx=601;ny=701
native=json.load(open(P/'manifests/routing-power-large-v12.json'))['result']
for v in native['vias']:vias.append({'net':v['net'],'x':v['x']*.0254,'y':v['y']*.0254,'diameter':v['diameter']*.0254,'hole':v['hole']*.0254})
for l in native['lines']:
 tracks.append({'net':l['net'],'layer':l['layer'],'points':[(l['x1']*.0254,l['y1']*.0254),(l['x2']*.0254,l['y2']*.0254)],'geom':LineString([(l['x1']*.0254,l['y1']*.0254),(l['x2']*.0254,l['y2']*.0254)]).buffer(l['width']*.0254/2)})
for r in native['polys']:
 if r['layer'] not in layers or not r['net']:continue
 p=r['polygon'];assert p[2]=='L' and all(isinstance(v,(int,float)) for v in p[3:]),p
 pts=[(p[0]*.0254,p[1]*.0254)]+[(p[i]*.0254,p[i+1]*.0254) for i in range(3,len(p),2)]
 tracks.append({'net':r['net'],'layer':r['layer'],'points':pts,'geom':LineString(pts).buffer(r['width']*.0254/2)})

base_obstacles=obstacles
def obstacles(net,layer,ignore=()):
 g=base_obstacles(net,layer,ignore)
 if layer==16 and net!='GND':g=unary_union([g,box(16.4,54.8,24,61.5),box(27.3,38.0,35,43.4)])
 return g
