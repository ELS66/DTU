import json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path('PCB/.tools').resolve()))
from shapely.geometry import box,Polygon,Point
from shapely.affinity import rotate,translate,scale
from shapely.ops import unary_union
P=Path('PCB');cs=json.load(open(P/'manifests/pcb-pads-layout-v12.json',encoding='utf-8'))['result'];by={c['ref']:c for c in cs};fps=json.load(open(P/'manifests/footprint-geometries-v12.json',encoding='utf-8'))
mov=['C90','C91','C92','C93','C94','C95','R90','R91','C96','C97','C98','C99','C106','C107','C108','C109','R92','R93','D14','C50','C51','R50','D10','R15','R16','R60','R61','D18','D19','D20','D21']
pos={r:[c['x']*.0254,c['y']*.0254,c['rotation'],c['layer']] for r,c in by.items()};local={};shapes={}
for c in cs:
 r=c['ref'];out=[]
 for q in c['pads']:
  if q['shape'][0]=='POLYGON':continue
  w,h=[z*.0254 for z in q['shape'][1:3]];g=rotate(box(-w/2,-h/2,w/2,h/2),q['rotation'],origin=(0,0));g=translate(g,(q['x']-c['x'])*.0254,(q['y']-c['y'])*.0254);out.append(g)
 for b in fps[c['footprint']['uuid']]:
  if b['type']=='POLY' and b.get('layerId')==48:
   nums=[z*.0254 for z in b['path'] if isinstance(z,(int,float))];g=Polygon(list(zip(nums[::2],nums[1::2])))
   if c['layer']==2:g=scale(g,xfact=-1,origin=(0,0))
   out.append(rotate(g,c['rotation'],origin=(0,0)))
 local[r]=unary_union(out)
def geom(r,p):
 c=by[r];g=rotate(local[r],p[2]-c['rotation'],origin=(0,0));return translate(g,p[0],p[1])
def pad(r,num,p=None):
 c=by[r];q=next(q for q in c['pads'] if q['number']==num);p=p or pos[r];a=math.radians(p[2]-c['rotation']);dx=(q['x']-c['x'])*.0254;dy=(q['y']-c['y'])*.0254;return(p[0]+dx*math.cos(a)-dy*math.sin(a),p[1]+dx*math.sin(a)+dy*math.cos(a))
mov=['C54']
shapes={r:geom(r,p) for r,p in pos.items() if r not in mov}
holes=[Point(x,y).buffer(3.4) for x,y in [(4,4),(46,4),(4,56),(46,56)]]
th=[Point(q['x']*.0254,q['y']*.0254).buffer(.9) for c in cs for q in c['pads'] if q['layer']==12]
def valid(r,g):
 if not box(.5,.5,49.5,59.5).covers(g) or any(g.intersects(h) for h in holes):return False
 if pos[r][3]==2 and any(g.intersects(h) for h in th):return False
 return not any(g.distance(q)<.3 for k,q in shapes.items() if k!=r and pos[k][3]==pos[r][3])
def place(r,target,num):
 opts=[];q=by[r]
 for rot in [0,90,180,270]:
  offset=pad(r,num,[0,0,rot,q['layer']]);cx,cy=target[0]-offset[0],target[1]-offset[1]
  for i in range(-35,36):
   for j in range(-35,36):
    x=round(cx+i*.2,3);y=round(cy+j*.2,3);dist=math.hypot(i*.2,j*.2);opts.append((dist+.008*math.dist((x,y),target),x,y,rot))
 for cost,x,y,rot in sorted(opts):
  p=[x,y,rot,q['layer']];g=geom(r,p)
  if valid(r,g):pos[r]=p;shapes[r]=g;return
 raise Exception('No placement '+r)

for r,root,pn,num in [('C54','J4','CD','1')]:
 place(r,pad(root,pn),num);print(r,pos[r],flush=True)
changed={r:{'id':by[r]['id'],'x':p[0],'y':p[1],'rotation':p[2]} for r,p in pos.items() if r in mov}
(P/'manifests/sim-detect-placement-v12.json').write_text(json.dumps(changed,indent=2),encoding='utf-8')
s=(P/'scripts/read-pcb-pads-v12.js').read_text();guard=s[:s.index('const out=')]
code=guard+'const moves='+json.dumps(changed)+";for(const s of Object.values(moves)){const c=await eda.pcb_PrimitiveComponent.get(s.id);const a=c.toAsync();a.setState_X(s.x/.0254);a.setState_Y(s.y/.0254);a.setState_Rotation(s.rotation);await a.done();}return await eda.pcb_Document.save();"
(P/'scripts/apply-sim-detect-placement-v12.js').write_text(code,encoding='utf-8')
