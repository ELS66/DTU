from pathlib import Path
import json
P=Path('PCB');c=json.loads((P/'reports/pcb-rules-v04.json').read_text(encoding='utf-8-sig'))['result']['rules']['config'];print(json.dumps(c['Physics'],indent=2)[:6000])
plan=json.loads((P/'manifests/pcb-layout-plan-v04.json').read_text());pos=plan['positions'];b=pos['L2']['bboxMm'];dx=(b[2]-b[0])/2;dy=(b[3]-b[1])/2;out=[]
for ix in range(20,100):
 for iy in range(30,70):
  x=ix*.25;y=iy*.25;bb=[x-dx,y-dy,x+dx,y+dy];bad=[]
  for r,z in pos.items():
   if r=='L2':continue
   q=z['bboxMm'];g=3 if r=='U2'else.25
   if bb[0]<q[2]+g and bb[2]>q[0]-g and bb[1]<q[3]+g and bb[3]>q[1]-g:bad.append(r)
  if len(bad)<=2:out.append((len(bad),abs(x-8)+abs(y-21),x,y,bad))
print('L2 possible moves',sorted(out)[:15])
