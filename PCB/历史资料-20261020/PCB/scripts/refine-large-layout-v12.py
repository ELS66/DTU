from pathlib import Path
exec(Path('PCB/scripts/inspect-large-layout-v12.py').read_text().split('bad=[]')[0])
pos={r:[c['x']*.0254,c['y']*.0254,c['rotation'],c['layer']] for r,c in by.items()}
fixed={'C80':(9.8,38.0,90),'C85':(21.0,37.8,90),'J4':(12,27,-90),'SW4':(25.5,61.5,0)}
mov=['R51','R52','R53','R54','C52','C53','C55','C56','C57','D11','D12','D13','R55','C54']
for c in cs:
 pp=[]
 for q in c['pads']:
  if q['shape'][0]=='POLYGON':continue
  w,h=[z*.0254 for z in q['shape'][1:3]]
  pp.append(translate(rotate(box(-w/2,-h/2,w/2,h/2),q['rotation'],origin=(0,0)),q['x']*.0254,q['y']*.0254))
 body[c['ref']]=unary_union([body[c['ref']]]+pp)
local={r:translate(g,-pos[r][0],-pos[r][1]) for r,g in body.items()}
def geom(r,p):return translate(rotate(local[r],p[2]-by[r]['rotation'],origin=(0,0)),p[0],p[1])
def pad(r,n,p=None):
 c=by[r];q=next(z for z in c['pads'] if z['number']==n);p=p or pos[r];a=math.radians(p[2]-c['rotation']);dx=(q['x']-c['x'])*.0254;dy=(q['y']-c['y'])*.0254
 return p[0]+dx*math.cos(a)-dy*math.sin(a),p[1]+dx*math.sin(a)+dy*math.cos(a)
for r,z in fixed.items():pos[r][:3]=z
shapes={r:geom(r,p) for r,p in pos.items() if r not in mov}
slots=[]
for x,y in [(-196.845,-213.47),(137.795,-213.47)]:
 a=math.radians(pos['J4'][2]);slots.append(Point(pos['J4'][0]+(x*math.cos(a)-y*math.sin(a))*.0254,pos['J4'][1]+(x*math.sin(a)+y*math.cos(a))*.0254).buffer(.75))
holes=[Point(x,y).buffer(3.4) for x,y in [(4,4),(56,4),(4,66),(56,66)]]+slots
def place(r,target,n):
 options=[];layer=pos[r][3]
 for rot in [0,90,180,270]:
  dx,dy=pad(r,n,[0,0,rot,layer]);cx,cy=target[0]-dx,target[1]-dy
  for i in range(-24,25):
   for j in range(-24,25):options.append((math.hypot(i,j),round(cx+i*.2,3),round(cy+j*.2,3),rot))
 for _,x,y,rot in sorted(options):
  p=[x,y,rot,layer];g=geom(r,p)
  if not box(.8,.8,59.2,69.2).covers(g) or any(g.intersects(h) for h in holes):continue
  if any(g.distance(q)<.3 for k,q in shapes.items() if k!=r and pos[k][3]==layer):continue
  pos[r]=p;shapes[r]=g;return
 raise Exception('No placement '+r)
targets=[('R51','U2','13','1'),('R52','U2','12','1'),('R53','U2','11','1'),('C52','J4','C1','1'),('C53','J4','C1','1'),('C55','J4','C3','1'),('C56','J4','C2','1'),('C57','J4','C7','1'),('D11','J4','C7','1'),('D12','J4','C2','1'),('D13','J4','C3','1'),('R54','J4','C7','2'),('C54','U2','79','1'),('R55','U2','79','2')]
for r,root,n,pn in targets:place(r,pad(root,n),pn)
changed={r:{'id':by[r]['id'],'x':pos[r][0],'y':pos[r][1],'rotation':pos[r][2]} for r in list(fixed)+mov}
g=(P/'scripts/read-pcb-pads-v12.js').read_text().split('const out=')[0]
code=g+'const moves='+json.dumps(changed)+";for(const s of Object.values(moves)){const c=await eda.pcb_PrimitiveComponent.get(s.id);const a=c.toAsync();a.setState_X(s.x/.0254);a.setState_Y(s.y/.0254);a.setState_Rotation(s.rotation);await a.done();}return await eda.pcb_Document.save();"
(P/'scripts/apply-refined-large-layout-v12.js').write_text(code,encoding='utf8');(P/'manifests/refined-large-placement-v12.json').write_text(json.dumps(changed,indent=2),encoding='utf8')
print(changed)
