from pathlib import Path
exec(Path('PCB/scripts/router-v12.py').read_text().replace('pcb-pads-routing-v12.json','pcb-pads-current-v12.json'))
step=.1;nx=501;ny=601
native=json.load(open(P/'manifests/routing-current-full-v12.json'))['result']
for v in native['vias']:vias.append({'net':v['net'],'x':v['x']*.0254,'y':v['y']*.0254,'diameter':v['diameter']*.0254,'hole':v['hole']*.0254})
for l in native['lines']:
 tracks.append({'net':l['net'],'layer':l['layer'],'points':[(l['x1']*.0254,l['y1']*.0254),(l['x2']*.0254,l['y2']*.0254)],'geom':LineString([(l['x1']*.0254,l['y1']*.0254),(l['x2']*.0254,l['y2']*.0254)]).buffer(l['width']*.0254/2)})
for r in native['polys']:
 if r['layer'] not in layers or not r['net']:continue
 p=r['polygon'];assert p[2]=='L' and all(isinstance(v,(int,float)) for v in p[3:]),p
 pts=[(p[0]*.0254,p[1]*.0254)]+[(p[i]*.0254,p[i+1]*.0254) for i in range(3,len(p),2)]
 tracks.append({'net':r['net'],'layer':r['layer'],'points':pts,'geom':LineString(pts).buffer(r['width']*.0254/2)})
# Preserve existing ground reference fills under the short bottom USB section.
planes=json.load(open(P/'manifests/reference-planes-v12.json'))
for r in planes:
 if r['layer']==16:
  p=r['poly'];pts=[(p[0]*.0254,p[1]*.0254)]+[(p[i]*.0254,p[i+1]*.0254) for i in range(3,len(p),2)];tracks.append({'net':'GND','layer':16,'geom':Polygon(pts),'points':pts})
