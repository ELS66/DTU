exec(__import__('pathlib').Path('PCB/scripts/audit-smt-bodies-v13.py').read_text(encoding='utf8').split('overlap=[]')[0])
from shapely.geometry import LineString
from shapely.prepared import prep
plan=json.loads((M/'hy20-final-routing-source-v13.json').read_text());by={c['ref']:c for c in cs};body={b['ref']:b['geom'] for b in bodies}
def padgeom(p):
 w,h=[v*.0254 for v in p['shape'][1:3]]
 return translate(rotate(box(-w/2,-h/2,w/2,h/2),p['rotation'],origin=(0,0)),p['x']*.0254,p['y']*.0254)
results={}
for ref in ['D6','Q1']:
 c=by[ref];ox,oy=c['x']*.0254,c['y']*.0254
 connected=[r['id'] for r in plan['routes'] if r['layer']==1 and any(p['net']==r['net'] and min(math.dist(q,(p['x']*.0254,p['y']*.0254)) for q in [r['pointsMm'][0],r['pointsMm'][-1]])<.015 for p in c['pads'])]
 copper={}
 for net in {p['net'] for p in c['pads']}:
  copper[net]=prep(unary_union([padgeom(p) for a in cs if a['ref']!=ref for p in a['pads'] if p['net']!=net and p['layer'] in [1,12]]+[LineString(r['pointsMm']).buffer(r['widthMm']/2) for r in plan['routes'] if r['id'] not in connected and r['layer']==1 and r['net']!=net]+[Point(v['x'],v['y']).buffer(v['diameter']/2) for v in plan['vias'] if v['net']!=net]).buffer(.158))
 bodyobs=prep(unary_union([scale(a['geom'],xfact=1.05,yfact=1.05,origin='center') for a in bodies if a['ref']!=ref and a['ref'] not in ['C50','C51','R32','J6','J7']]))
 opts=[]
 for dr in ([0,90] if ref=='D6' else [0]):
  rbody=scale(rotate(body[ref],dr,origin=(ox,oy)),xfact=1.05,yfact=1.05,origin='center')
  rpads=[(p,rotate(padgeom(p),dr,origin=(ox,oy))) for p in c['pads']]
  for ix in range(-90,21):
   for iy in range(-110,51):
    dx,dy=ix*.1,iy*.1
    if ref=='Q1' and ox+dx<27.5:continue
    nb=translate(rbody,dx,dy)
    if bodyobs.intersects(nb):continue
    if any(copper[p['net']].intersects(translate(g,dx,dy)) for p,g in rpads):continue
    cost=math.hypot(dx,dy)+(.5 if dr else 0)
    opts.append({'x':ox+dx,'y':oy+dy,'rotation':c['rotation']+dr,'dx':dx,'dy':dy,'dr':dr,'cost':cost})
 opts.sort(key=lambda a:a['cost']);results[ref]={'connectedRoutes':connected,'candidates':opts[:20]}
(M/'smt-location-options-v13.json').write_text(json.dumps(results,indent=2),encoding='utf8')
print(json.dumps(results,indent=2))
