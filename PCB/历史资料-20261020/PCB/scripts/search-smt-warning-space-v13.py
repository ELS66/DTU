from pathlib import Path
import json,math
exec(Path('PCB/scripts/router-v13.py').read_text(encoding='utf8').replace('read-pcb-pads-v13.json','silkclean-pcb-pads-v13.json'))
from shapely.affinity import scale
from shapely.prepared import prep
plan=json.loads((P/'manifests/exposure-fixed-actual-routing-v13.json').read_text());dnps={'C50','C51','R32','J6','J7'}
# Physical body enlarged by 12%; include connector lead envelope when comparing to nearby components.
bounds={r['ref']:box(*r['bounds']) for r in json.loads((P/'manifests/silkholefix-body-audit-v13.json').read_text())['bounds']}
for ref in ['J4','Q1','C85']:
 c=by[ref];bounds[ref]=box(*[c['bbox'][f]*.0254 for f in ['minX','minY','maxX','maxY']])
result={}
for ref in ['C53','C57','C94','Q1']:
 c=by[ref];ox,oy=c['x']*.0254,c['y']*.0254
 connected=[r['id'] for r in plan['routes'] if r['layer']==1 and any(p['net']==r['net'] and min(math.dist(q,(p['x']*.0254,p['y']*.0254)) for q in [r['pointsMm'][0],r['pointsMm'][-1]])<.02 for p in c['pads'])]
 copper={}
 for net in {p['net'] for p in c['pads']}:
  copper[net]=prep(unary_union([p['geom'] for p in pads if p['ref']!=ref and p['net']!=net and p['layer'] in [1,12]]+[LineString(r['pointsMm']).buffer(r['widthMm']/2) for r in plan['routes'] if r['id'] not in connected and r['layer']==1 and r['net']!=net]+[Point(v['x'],v['y']).buffer(v['diameter']/2) for v in plan['vias'] if v['net']!=net]).buffer(.158))
 bodyobs=prep(unary_union([scale(g,xfact=1.12,yfact=1.12) for rr,g in bounds.items() if rr!=ref and rr not in dnps]));bg=scale(bounds[ref],xfact=1.12,yfact=1.12);pp=[p for p in pads if p['ref']==ref];opts=[]
 for ix in (range(-15,11) if ref=='Q1' else range(0,16)):
  for iy in (range(0,31) if ref=='Q1' else range(-5,6)):
   dx,dy=ix*.1,iy*.1
   if bodyobs.intersects(translate(bg,dx,dy)):continue
   if any(copper[p['net']].intersects(translate(p['geom'],dx,dy)) for p in pp):continue
   opts.append({'x':ox+dx,'y':oy+dy,'dx':dx,'dy':dy,'cost':math.hypot(dx,dy)})
 opts.sort(key=lambda q:q['cost']);result[ref]={'connected':connected,'candidates':opts[:10]}
(P/'manifests/smt-warning-location-options-v13.json').write_text(json.dumps(result,indent=2));print(ref,len(opts),opts[:3],flush=True)
