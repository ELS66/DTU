from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text().replace('pcb-pads-power-v07.json','pcb-pads-v09.json').replace('routing-power-v07.json','routing-pullup-v09.json'))
tracks[:]=[t for t in tracks if t['net'] not in ['SIM_DATA_M','SIM_RST_M','SIM_CLK_M']]
vias[:]=[v for v in vias if v['net'] not in ['SIM_DATA_M','SIM_RST_M','SIM_CLK_M']]
from shapely.affinity import rotate,translate
moves=[]
for ref,net,pin in [('R51','SIM_DATA_M','11'),('R52','SIM_RST_M','12'),('R53','SIM_CLK_M','13')]:
 c=next(c for c in cs if c['ref']==ref);cp=[p for p in pads if p['ref']==ref];oldx,oldy=c['x']*.0254,c['y']*.0254;other=unary_union([p['geom'] for p in pads if p['ref'] not in ['R51','R52','R53'] or p['ref'] in [z['ref'] for z in moves]]);obs={q['net']:obstacles(q['net'],1) for q in cp};cands=[];t=next(p for p in pads if p['ref']=='U2' and p['number']==pin)
 for x in np.arange(27,30,.2):
  for y in np.arange(31,37,.2):
   pp=[{**p,'geom':translate(rotate(p['geom'],180-c['rotation'],origin=(oldx,oldy)),xoff=x-oldx,yoff=y-oldy)} for p in cp]
   if any(q['geom'].distance(other)<.2 for q in pp) or any(q['geom'].buffer(.1525).intersects(obs[q['net']]) for q in pp):continue
   pw=next(q for q in pp if q['net']==net)['geom'].centroid;cands.append((pw.distance(Point(t['x'],t['y'])),x,y,pp))
 if not cands:raise Exception('No placement '+ref)
 _,x,y,pp=min(cands,key=lambda v:v[0]);moves.append({'ref':ref,'x':round(float(x),3),'y':round(float(y),3),'rotation':180});pads=[p for p in pads if p['ref']!=ref]+pp;print(moves[-1],flush=True)
(P/'manifests/sim-placement-preview-v09.json').write_text(json.dumps(moves,indent=2))
