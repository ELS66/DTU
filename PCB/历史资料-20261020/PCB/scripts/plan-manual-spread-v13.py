from pathlib import Path
s=Path('PCB/scripts/inspect-layout-v13.py').read_text(encoding='utf8');exec(s.split('bad=[]')[0])
from shapely.strtree import STRtree
from shapely.ops import unary_union
base={}
for c in cs:
 gs=[body[c['ref']]]
 for q in c['pads']:
  if q['shape'][0]=='POLYGON':
   a=[v*.0254 for v in q['shape'][1] if isinstance(v,(int,float))];g=Polygon(list(zip(a[::2],a[1::2])))
  else:
   w,h=[v*.0254 for v in q['shape'][1:3]];g=Point(0,0).buffer(max(w,h)/2) if q['shape'][0]=='ELLIPSE' else box(-w/2,-h/2,w/2,h/2);g=translate(rotate(g,q['rotation'],origin=(0,0)),q['x']*.0254,q['y']*.0254)
  gs.append(g)
 base[c['ref']]=unary_union(gs).buffer(.17)
rows=[];moving={'RN5','C52','RN2'};occupied=[g for ref,g in base.items() if ref not in moving];occupied+=[Point(x,y).buffer(3.4) for x,y in [(4,4),(56,4),(4,66),(56,66)]]
for ref,tx,ty,tr in [('C52',25.5,32.35,0),('RN2',5,32.5,90),('RN5',5.5,39,90)]:
 c=by[ref];g=rotate(translate(base[ref],-c['x']*.0254,-c['y']*.0254),-c['rotation'],origin=(0,0));opts=[]
 for ix in range(-16,17):
  for iy in range(-16,17):opts.append((ix*ix+iy*iy,tx+ix*.25,ty+iy*.25))
 for _,x,y in sorted(opts):
  q=translate(rotate(g,tr,origin=(0,0)),x,y)
  if not box(.3,8.5,59.7,69.7).covers(q) or any(q.intersects(z) for z in occupied):continue
  rows.append([ref,x,y,tr]);occupied.append(q);break
 else:
  q=translate(rotate(g,tr,origin=(0,0)),tx,ty);print('BLOCKED',ref,q.bounds,[(r,z.bounds) for r,z in base.items() if r not in moving and q.intersects(z)],'rows',rows);raise Exception('Cannotplace '+ref)
print(rows)
Path('PCB/manifests/manual-spread-v13.json').write_text(json.dumps(rows),encoding='utf8')
guard=Path('PCB/scripts/read-pcb-pads-v13.js').read_text(encoding='utf8').split('const out=')[0]
Path('PCB/scripts/manual-spread-v13.js').write_text(guard+'const rows='+json.dumps(rows)+';const cs=await eda.pcb_PrimitiveComponent.getAll();for(const [ref,x,y,rotation] of rows){const c=cs.find(c=>c.getState_Designator()===ref);if(!await eda.pcb_PrimitiveComponent.modify(c,{x:x/.0254,y:y/.0254,rotation}))throw Error(ref);}return await eda.pcb_Document.save();',encoding='utf8')
