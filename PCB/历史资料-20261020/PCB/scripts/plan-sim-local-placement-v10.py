from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text().replace('pcb-pads-power-v07.json','pcb-pads-start-v10.json').replace('routing-power-v07.json','routing-sim-local-preview-v10.json'))
from shapely.affinity import rotate,translate
moves=[]
for ref,net,pin in [('C52','SIM_VDD','C1'),('C53','SIM_VDD','C1'),('C54','SIM_DET','CD'),('D12','SIM_RST','C2'),('D11','SIM_DATA','C7')]:
 c=next(c for c in cs if c['ref']==ref);cp=[p for p in pads if p['ref']==ref];ox,oy=c['x']*.0254,c['y']*.0254;other=[p for p in pads if p['ref']!=ref];hulls=unary_union([unary_union([p['geom'] for p in other if p['ref']==cc['ref']]).convex_hull for cc in cs if cc['ref']!=ref]);obs={q['net']:obstacles(q['net'],1) for q in cp};t=next(p for p in pads if p['ref']=='J4' and p['number']==pin);out=[]
 for rot in [0,90,180,270]:
  rp=[{**p,'geom':rotate(p['geom'],rot-c['rotation'],origin=(ox,oy))} for p in cp]
  for x in np.arange(16,20,.2):
   for y in np.arange(t['y']-3.0,t['y']+3.0,.2):
    pp=[{**q,'geom':translate(q['geom'],xoff=x-ox,yoff=y-oy)} for q in rp];h=unary_union([q['geom'] for q in pp]).convex_hull
    if h.distance(hulls)<.15 or any(q['geom'].buffer(.1525).intersects(obs[q['net']]) for q in pp):continue
    q=next(q for q in pp if q['net']==net)['geom'].centroid;out.append((q.distance(Point(t['x'],t['y'])),x,y,rot,pp))
 if not out:raise Exception('No placement '+ref)
 _,x,y,rot,pp=min(out,key=lambda q:q[0]);moves.append({'ref':ref,'x':round(float(x),5),'y':round(float(y),5),'rotation':rot});pads=[p for p in pads if p['ref']!=ref]+pp;print(moves[-1],flush=True)
(P/'manifests/sim-local-placement-v10.json').write_text(json.dumps(moves,indent=2))
