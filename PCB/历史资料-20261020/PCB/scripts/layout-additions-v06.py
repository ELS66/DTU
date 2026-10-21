from pathlib import Path
import json,math
p=Path('PCB');cs=json.loads((p/'manifests/pcb-before-layout-v06.json').read_text(encoding='utf-8-sig'))['result'];by={c['ref']:c for c in cs};new=[r for r,c in by.items() if c['x']*.0254>60];boxes={};placed={};fail=[]
for r,c in by.items():
 if r[0] in 'UJL' or r=='C80':continue
 pts=[]
 for q in c['pads']:
  w,h=q['shape'][1:3];a=math.radians(q['rotation'])
  for dx in [-w/2,w/2]:
   for dy in [-h/2,h/2]:pts.append((q['x']+dx*math.cos(a)-dy*math.sin(a),q['y']+dx*math.sin(a)+dy*math.cos(a)))
 b={'minX':min(z[0] for z in pts)-3,'maxX':max(z[0] for z in pts)+3,'minY':min(z[1] for z in pts)-3,'maxY':max(z[1] for z in pts)+3}
 if r.startswith('SW'):
  b['minY']=min(b['minY'],c['y']-1.8/.0254);b['maxY']=max(b['maxY'],c['y']+1.8/.0254)
 if r in ['D1','D2','D3']:
  b['minY']=min(b['minY'],c['y']-1.4/.0254);b['maxY']=max(b['maxY'],c['y']+1.4/.0254)
 c['bbox']=b

def box(r,x,y,rot):
 c=by[r];b=c['bbox'];a=math.radians(rot-c['rotation']);pts=[]
 for xx in [b['minX'],b['maxX']]:
  for yy in [b['minY'],b['maxY']]:
   dx=(xx-c['x'])*.0254;dy=(yy-c['y'])*.0254;pts.append((x+dx*math.cos(a)-dy*math.sin(a),y+dx*math.sin(a)+dy*math.cos(a)))
 return [min(z[0] for z in pts),min(z[1] for z in pts),max(z[0] for z in pts),max(z[1] for z in pts)]
def overlap(a,b,g):return a[0]<b[2]+g and a[2]>b[0]-g and a[1]<b[3]+g and a[3]>b[1]-g
for r,c in by.items():
 if r not in new:placed[r]=[c['x']*.0254,c['y']*.0254,c['rotation']];boxes[r]=box(r,*placed[r])
def valid(r,b):return b[0]>=.4 and b[1]>=.4 and b[2]<=59.6 and b[3]<=69.6 and not any(overlap(b,bb,3 if k=='U2' else .25) for k,bb in boxes.items())
grid=[(x*.4,y*.4) for x in range(2,149) for y in range(2,174)]
def put(r,target,rots=[0,90]):
 for x,y in sorted(grid,key=lambda z:(z[0]-target[0])**2+(z[1]-target[1])**2):
  for rot in rots:
   b=box(r,x,y,rot)
   if valid(r,b):placed[r]=[x,y,rot];boxes[r]=b;return
 fail.append(r)
for r,t in [('J6',(13,64)),('J7',(39,54.7)),('U10',(21.8,32.1)),('U8',(41,12)),('C110',(33,24))]:put(r,t)
for start,target in [(30,(1.6,63)),(33,(55.6,41))]:
 found=False
 for x,y in sorted(grid,key=lambda z:(z[0]-target[0])**2+(z[1]-target[1])**2):
  candidate={f'D{start+i}':(x,y-i*4,0) for i in range(3)}
  if all(valid(r,box(r,*pos)) for r,pos in candidate.items()):
   for r,pos in candidate.items():placed[r]=list(pos);boxes[r]=box(r,*pos)
   found=True;break
 if not found:fail.extend(candidate)
put('D36',(43,66));put('D37',(48,66))
for i in range(8):
 r=f'R{140+i}';d=f'D{30+i}';x,y,rot=placed[d];put(r,(x+2.4,y))
if fail:raise Exception(fail)
plan={'version':'V0.6','new':new,'newPositions':{r:{'xMm':placed[r][0],'yMm':placed[r][1],'rotation':placed[r][2],'bboxMm':boxes[r]} for r in new},'unplaced':fail};(p/'manifests/pcb-additions-layout-v06.json').write_text(json.dumps(plan,indent=2))
a=[{'ref':r,'x':placed[r][0]/.0254,'y':placed[r][1]/.0254,'rotation':placed[r][2]} for r in new]
base='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");'
for i in range(0,len(a),12):
 s=base+'const specs='+json.dumps(a[i:i+12])+';const cs=await eda.pcb_PrimitiveComponent.getAll();for(const z of specs){const c=cs.find(c=>c.getState_Designator()===z.ref);if(!c)throw Error("Missing "+z.ref);await eda.pcb_PrimitiveComponent.modify(c,{x:z.x,y:z.y,rotation:z.rotation});}return {saved:await eda.pcb_Document.save(),placed:specs.map(z=>z.ref)};';(p/f'scripts/place-additions-v06-{i//12+1}.js').write_text(s)
print(json.dumps(plan))

