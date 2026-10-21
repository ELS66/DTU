import json,math
from pathlib import Path
p=Path('PCB');cs=json.loads((p/'manifests/pcb-pads-before-v07.json').read_text(encoding='utf-8-sig'))['result'];by={c['ref']:c for c in cs};mov=['U4','L1','U5','L2','U11','L3','D14','C80']+[f'C{k}' for k in list(range(90,100))+list(range(106,110))]+['R90','R91','R92','R93'];pos={};boxes={};failed=[]
for r,c in by.items():
 if r[0] in 'UJL' or r=='C80':continue
 pts=[]
 for q in c['pads']:
  w,h=q['shape'][1:3];ang=math.radians(q['rotation'])
  for dx in [-w/2,w/2]:
   for dy in [-h/2,h/2]:pts.append((q['x']+dx*math.cos(ang)-dy*math.sin(ang),q['y']+dx*math.sin(ang)+dy*math.cos(ang)))
 c['bbox']={'minX':min(z[0] for z in pts)-3,'minY':min(z[1] for z in pts)-3,'maxX':max(z[0] for z in pts)+3,'maxY':max(z[1] for z in pts)+3}
 if r.startswith('SW'):
  c['bbox']['minY']=min(c['bbox']['minY'],c['y']-1.8/.0254);c['bbox']['maxY']=max(c['bbox']['maxY'],c['y']+1.8/.0254)
 if r in ['D1','D2','D3']:
  c['bbox']['minY']=min(c['bbox']['minY'],c['y']-1.4/.0254);c['bbox']['maxY']=max(c['bbox']['maxY'],c['y']+1.4/.0254)
def box(r,x,y,rot):
 c=by[r];b=c['bbox'];ang=math.radians(rot-c['rotation']);pts=[]
 for xx in [b['minX'],b['maxX']]:
  for yy in [b['minY'],b['maxY']]:
   dx=(xx-c['x'])*.0254;dy=(yy-c['y'])*.0254;pts.append((x+dx*math.cos(ang)-dy*math.sin(ang),y+dx*math.sin(ang)+dy*math.cos(ang)))
 return [min(z[0] for z in pts),min(z[1] for z in pts),max(z[0] for z in pts),max(z[1] for z in pts)]
def overlap(a,b,g=.25):return a[0]<b[2]+g and a[2]>b[0]-g and a[1]<b[3]+g and a[3]>b[1]-g
for r,c in by.items():
 if r not in mov:pos[r]=[c['x']*.0254,c['y']*.0254,c['rotation']];boxes[r]=box(r,*pos[r])
def valid(r,b):return b[0]>=.4 and b[1]>=.4 and b[2]<=59.6 and b[3]<=69.6 and not any(overlap(b,v,3 if k=='U2' else .25) for k,v in boxes.items())
def pad(r,num,at=None):
 c=by[r];q=next(q for q in c['pads'] if q['number']==num);x,y,rot=at or pos[r];ang=math.radians(rot-c['rotation']);dx=(q['x']-c['x'])*.0254;dy=(q['y']-c['y'])*.0254;return (x+dx*math.cos(ang)-dy*math.sin(ang),y+dx*math.sin(ang)+dy*math.cos(ang))
grid=[(x*.3,y*.3) for x in range(3,198) for y in range(3,231)]
def place(r,target,pin=None):
 cand=[]
 for x,y in sorted(grid,key=lambda z:math.dist(z,target))[:10000]:
  for rot in [0,90,180,270]:
   b=box(r,x,y,rot)
   if not valid(r,b):continue
   dest=pad(r,pin,[x,y,rot]) if pin else (x,y);score=math.dist(dest,target)+.01*math.dist((x,y),target)
   cand.append((score,[x,y,rot],b))
   if len(cand)>100:break
  if len(cand)>100:break
 if not cand:raise Exception('No placement '+r)
 _,v,b=min(cand);pos[r]=v;boxes[r]=b
place('C80',pad('U2','42'),pin='1')
def pair(ic,ind,target):
 opts=[]
 for x,y in sorted(grid,key=lambda z:math.dist(z,target))[:180]:
  for rot in [0,90,180,270]:
   b=box(ic,x,y,rot)
   if not valid(ic,b):continue
   sw=pad(ic,'5' if ic!='U11' else '1',[x,y,rot])
   for ir in [0,90,180,270]:
    ox,oy=pad(ind,'1' if ind!='L3' else '2',[0,0,ir])
    for d in [.7,1.1,1.6,2.2,2.8,3.4]:
     for vx,vy in [(1,0),(-1,0),(0,1),(0,-1),(.707,.707),(.707,-.707),(-.707,.707),(-.707,-.707)]:
      ix=round((sw[0]-ox+vx*d)/.1)*.1;iy=round((sw[1]-oy+vy*d)/.1)*.1;ib=box(ind,ix,iy,ir)
      if not valid(ind,ib) or overlap(b,ib):continue
      ip=pad(ind,'1' if ind!='L3' else '2',[ix,iy,ir]);dist=math.dist(sw,ip)
      opts.append((dist+.12*math.dist((x,y),target),[x,y,rot],b,[ix,iy,ir],ib))
   if len(opts)>150:break
  if len(opts)>150:break
 if not opts:raise Exception('No pair '+ic)
 _,v,b,iv,ib=min(opts);pos[ic]=v;boxes[ic]=b;pos[ind]=iv;boxes[ind]=ib
pair('U4','L1',(30,61));pair('U5','L2',(10,18));pair('U11','L3',(55.4,56));place('D14',pad('U11','1'),pin='2')
for r,root,num,mypin in [('C92','U4','6','1'),('C91','U4','3','1'),('C90','U4','3','1'),('C93','L1','2','1'),('C94','L1','2','1'),('R90','U4','1','2'),('R91','U4','1','1'),('C95','U4','1','2'),('C97','U5','6','1'),('C106','U5','3','1'),('C96','U5','3','1'),('C98','L2','2','1'),('C99','L2','2','1'),('C107','L3','1','1'),('C108','D14','1','1'),('R92','U11','3','2'),('R93','U11','3','1'),('C109','U11','3','2')]:place(r,pad(root,num),pin=mypin)
new={r:{'xMm':pos[r][0],'yMm':pos[r][1],'rotation':pos[r][2],'bboxMm':boxes[r]} for r in mov};metrics={}
for ic,l,num,pn in [('U4','L1','5','1'),('U5','L2','5','1'),('U11','L3','1','2'),('U2','C80','42','1')]:
 old=math.dist(pad(ic,num,[by[ic]['x']*.0254,by[ic]['y']*.0254,by[ic]['rotation']]),pad(l,pn,[by[l]['x']*.0254,by[l]['y']*.0254,by[l]['rotation']]));metrics[ic+'-'+l]={'beforeMm':old,'afterMm':math.dist(pad(ic,num),pad(l,pn))}
plan={'positions':new,'metrics':metrics};(p/'manifests/power-layout-v07.json').write_text(json.dumps(plan,indent=2));print(json.dumps(metrics));print('positions',json.dumps({r:pos[r] for r in ['U4','L1','U5','L2','U11','L3','D14','C80']}))
