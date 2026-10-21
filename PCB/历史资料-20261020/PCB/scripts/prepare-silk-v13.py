import json,math
from pathlib import Path
exec(Path('PCB/scripts/router-v13.py').read_text(encoding='utf8'))
exec(Path('PCB/scripts/inspect-layout-v13.py').read_text(encoding='utf8'))
from shapely.geometry import box,LineString
mask=unary_union([p['geom'].buffer(.025) for p in pads])
blocked=unary_union([mask.buffer(.2),*holes[:4]])
used=[];labels=[];hidden=[]
def rect(x,y,text,size):return box(x-(len(text)*.67*size+.18)/2,y-(size+.18)/2,x+(len(text)*.67*size+.18)/2,y+(size+.18)/2)
def add(x,y,text,size=1,ref=None,force=False):
 g=rect(x,y,text,size)
 if not force and (not box(.4,.4,59.6,69.6).covers(g) or blocked.intersects(g) or any(g.distance(u)<.14 for u in used)):return False
 labels.append(dict(x=x,y=y,text=text,size=size,ref=ref));used.append(g);return True
for x,name,ps in [(16.5,'J1 RS485','PABG'),(30,'J2 RS232','PTRG'),(43.5,'J3 UART','PTRG')]:
 for i,s in enumerate(ps):assert add(x+(i-1.5)*2,6.5,s)
 assert add(x,8,name)
for ref,name,ps in [('J7','J7 LTE DL',['G','D+','D-','VB','B']),('J6','J6 ESP DL',['G','D+','D-','EN','B'])]:
 c=by[ref];x=c['x']*.0254
 assert add(x,65.5,name)
 pp=sorted(c['pads'],key=lambda q:q['x'])
 for q,s in zip(pp,ps):assert add(q['x']*.0254,67.15,s)
assert add(30,68.8,'DTU V0.13',1.1)
add(11,63,'LTE ANT')
for x,t in [(38.5,'TX'),(47,'RX')]:add(x,33.1,t)
ex={'J1','J2','J3','J5','J6','J7','D36','D37'}
bodyblock=unary_union([v.buffer(.12) for v in body.values()])
for c in sorted(cs,key=lambda c:(not c['ref'].startswith('U'),-len(c['ref']))):
 ref=c['ref']
 if ref in ex:continue
 cx,cy=c['x']*.0254,c['y']*.0254
 choices=[]
 for dx in range(-24,25):
  for dy in range(-24,25):
   x,y=cx+dx*.25,cy+dy*.25;cost=math.hypot(x-cx,y-cy)
   if cost>6:continue
   g=rect(x,y,ref,1)
   if not g.intersects(bodyblock):choices.append((cost,x,y))
 for _,x,y in sorted(choices):
  if add(x,y,ref,1,ref):break
 else:hidden.append(ref)
# Preserve library outline and polarity geometry, clip mask openings, increase strokes below .15mm.
lines=[]
for c in cs:
 for primitive in fps[c['footprint']['uuid']]:
  if primitive.get('layerId')!=3 or primitive['type'] not in ['POLY','FILL']:continue
  paths=[primitive['path']] if primitive['type']=='POLY' else primitive['path']
  w=max(.15,primitive.get('width',6)*.0254) if primitive['type']=='POLY' else .15
  for path in paths:
   pts=[]
   if path[0]=='CIRCLE':
    _,x,y,r=path;pts=[((x+r*math.cos(k*math.pi/12))*.0254,(y+r*math.sin(k*math.pi/12))*.0254) for k in range(25)]
   else:
    pts=[(path[0]*.0254,path[1]*.0254)];i=2
    while i<len(path):
     if path[i]=='L':i+=1;continue
     if path[i]=='ARC':
      theta=math.radians(path[i+1]);z=(path[i+2]*.0254,path[i+3]*.0254);p0=pts[-1];dx,dy=z[0]-p0[0],z[1]-p0[1]
      cx=(p0[0]+z[0])/2-dy/(2*math.tan(theta/2));cy=(p0[1]+z[1])/2+dx/(2*math.tan(theta/2));vx,vy=p0[0]-cx,p0[1]-cy
      for k in range(1,17):
       t=theta*k/16;pts.append((cx+vx*math.cos(t)-vy*math.sin(t),cy+vx*math.sin(t)+vy*math.cos(t)))
      i+=4
     else:pts.append((path[i]*.0254,path[i+1]*.0254));i+=2
   if len(pts)<2:continue
   g=translate(rotate(LineString(pts),c['rotation'],origin=(0,0)),c['x']*.0254,c['y']*.0254)
   other=unary_union([v for r,v in body.items() if r!=c['ref']])
   forbid=unary_union([mask.buffer(.15+w/2+.015),*holes[:4],*[u.buffer(.12+w/2) for u in used],other.buffer(.02+w/2)])
   clipped=g.difference(forbid).intersection(box(.3,.3,59.7,69.7))
   for q in clipped.geoms if hasattr(clipped,'geoms') else [clipped]:
    if q.geom_type=='LineString' and q.length>.20:lines.append(dict(points=list(q.coords),width=w,ref=c['ref']))
marks=[]
# Explicit positive marks remain close to the positive ends of both bulk capacitors.
for ref in ['C80','C85']:
 pin=next(p for p in pads if p['ref']==ref and p['number']=='1')
 for dx,dy in [(-.7,2),(-.7,-2),(-2.8,1.7),(-2.8,-1.7)]:
  if add(pin['x']+dx,pin['y']+dy,'+'):break
 else:marks.append(ref)
plan=dict(labels=labels,lines=lines,unplacedReferences=hidden,unplacedPolarity=marks)
(P/'manifests/silk-v13.json').write_text(json.dumps(plan,indent=2),encoding='utf8')
guard=(P/'scripts/read-pcb-pads-v13.js').read_text().split('const out=')[0]
code=guard+"if((await eda.pcb_PrimitiveString.getAll()).length)throw Error('Existing standalone silk requires review');let n=0;for(const a of await eda.pcb_PrimitiveAttribute.getAll()){if(a.getState_Key()==='Designator'||a.getState_Key()==='Name')await eda.pcb_PrimitiveAttribute.modify(a,{keyVisible:false,valueVisible:false});}const labels="+json.dumps(labels)+";const ids=[];for(const z of labels){const s=await eda.pcb_PrimitiveString.create(3,z.x/.0254,z.y/.0254,z.text,'default',z.size/.0254,.15/.0254,5,0,false,0,false,false);if(!s)throw Error('Silk failed');ids.push(s.getState_PrimitiveId());}return {count:ids.length,ids,saved:await eda.pcb_Document.save()};"
(P/'scripts/apply-silk-text-v13.js').write_text(code,encoding='utf8')
for i in range(0,len(lines),25):
 code=guard+'const lines='+json.dumps(lines[i:i+25])+";let n=0;for(const p of lines){const v=p.points.map(q=>q.map(z=>z/.0254));const path=[...v[0],'L',...v.slice(1).flat()];if(!await eda.pcb_PrimitivePolyline.create('',3,eda.pcb_MathPolygon.createPolygon(path),p.width/.0254,false))throw Error('Silk line');n++;}return {count:n,saved:await eda.pcb_Document.save()};"
 (P/f'scripts/apply-silk-lines-v13-{i//25+1}.js').write_text(code,encoding='utf8')
print('labels',len(labels),'lines',len(lines),'hidden',hidden,'no marks',marks)
