import json
from pathlib import Path
x=json.loads(Path('PCB/reports/ground-plane-v07.json').read_text(encoding='utf-8-sig'))['result']['layers'];print([z for z in x if z['id'] in [15,16]])
f=Path('PCB/scripts/plan-power-v07.py');s=f.read_text(encoding='utf-8-sig');start=s.index('def pair(');end=s.index("pair('U4'",start);s=s[:start]+'''def pair(ic,ind,target):
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
''' + s[end:];f.write_text(s,encoding='utf-8')
