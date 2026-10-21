from pathlib import Path
import json,math
P=Path('PCB');cs=json.loads((P/'manifests/pcb-stage-pads-v04.json').read_text(encoding='utf-8-sig'))['result'];by={c['ref']:c for c in cs};m=json.loads((P/'manifests/design.json').read_text(encoding='utf-8'));meta={p['ref']:p for p in m['parts']};W,H=60,70;placed={};bboxes={};fail=[]
for c in cs:
 ref=c['ref']
 if ref[0]in 'UJL'or ref=='C80':continue
 pts=[]
 for pad in c['pads']:
  shape=pad['shape'];w=shape[1];h=shape[2];a=math.radians(pad['rotation'])
  for dx in [-w/2,w/2]:
   for dy in [-h/2,h/2]:pts.append((pad['x']+dx*math.cos(a)-dy*math.sin(a),pad['y']+dx*math.sin(a)+dy*math.cos(a)))
 b={'minX':min(p[0]for p in pts)-3,'minY':min(p[1]for p in pts)-3,'maxX':max(p[0]for p in pts)+3,'maxY':max(p[1]for p in pts)+3}
 if ref.startswith('SW'):
  b['minY']=min(b['minY'],c['y']-1.8/.0254);b['maxY']=max(b['maxY'],c['y']+1.8/.0254)
 if ref in ['D1','D2','D3']:
  b['minY']=min(b['minY'],c['y']-1.4/.0254);b['maxY']=max(b['maxY'],c['y']+1.4/.0254)
 c['bbox']=b
fixed={'U1':(14,48,0),'U2':(39,40,0),'J1':(9,3.3,0),'J2':(27,3.3,0),'J3':(44,3.3,0),'J4':(8.12,28,270),'J5':(53,47,0),'J6':(5.3,63,270),'J7':(54.7,21.2,90),'U3':(19,8,0),'U4':(30,61,0),'L1':(37,60,0),'C80':(47,60,0),'U5':(8,18,0),'L2':(18.8,18,0),'U11':(55.4,56,0),'L3':(55.4,61,180),'D14':(52.4,55,90),'U6':(8.5,11.7,0),'U7':(27,12,0),'U8':(41,12,0),'U12':(44.5,18,0),'U13':(21.7,24.8,0),'U9':(40,21,0),'U14':(33,22,0),'U10':(21.8,32.1,0)}
def box(ref,x,y,r):
 c=by[ref];b=c['bbox'];a=math.radians(r-c['rotation']);pts=[]
 for xx in [b['minX'],b['maxX']]:
  for yy in [b['minY'],b['maxY']]:
   dx=(xx-c['x'])*.0254;dy=(yy-c['y'])*.0254;pts.append((x+dx*math.cos(a)-dy*math.sin(a),y+dx*math.sin(a)+dy*math.cos(a)))
 return [min(p[0]for p in pts),min(p[1]for p in pts),max(p[0]for p in pts),max(p[1]for p in pts)]
def overlap(a,b,g):return a[0]<b[2]+g and a[2]>b[0]-g and a[1]<b[3]+g and a[3]>b[1]-g
def valid(ref,b):
 if b[0]<.4 or b[1]<.4 or b[2]>W-.4 or b[3]>H-.4:return False
 return not any(overlap(b,bb,3 if k=='U2'or ref=='U2'else .25)for k,bb in bboxes.items())
for ref,(x,y,r) in fixed.items():
 b=box(ref,x,y,r)
 bad=[k for k,bb in bboxes.items()if overlap(b,bb,3 if k=='U2'or ref=='U2'else .25)]
 if b[0]<0 or b[1]<0 or b[2]>W or b[3]>H or bad:print('FIXED CONFLICT',ref,[round(v,2)for v in b],bad)
 placed[ref]=[x,y,r];bboxes[ref]=b

targets={1:(20,8),2:(13,48),3:(39,44),4:(8,28),5:(28,13),6:(31,24),7:(22,31),8:(18,19)}
owner={}
for ref in by:
 if ref.startswith('C'):
  k=int(ref[1:]);owner[ref]='U4'if 90<=k<=95 else 'U5'if 96<=k<=99 or k==106 else 'U11'if 107<=k<=109 else 'U7'if 30<=k<=34 else 'U6'if k==35 else 'U8'if k in [36,37]else 'U12'if k==38 else 'U10'if k in [70,71]else 'U2'if 80<=k<=84 else 'U14'if 100<=k<=102 else 'U13'if k==103 else 'U9'if k==104 else 'U14'if k==105 else 'U3'if k<=4 else 'U1'if 10<=k<=12 else 'J4'
 if ref.startswith('R'):
  k=int(ref[1:]);owner[ref]='U4'if k in [90,91]else 'U11'if k in [92,93]else 'U6'if k in [30,31,32]else 'U7'if k in [33,34]else 'U8'if k==35 else 'U12'if k in [36,37]else 'U14'if 100<=k<=117 else 'U10'if 70<=k<=87 else 'U3'if k<=6 else 'J6'if 15<=k<=18 else 'J7'if 60<=k<=63 else 'J4'if 51<=k<=55 else 'J5'if k==50 else 'U1'if 10<=k<=14 else 'U9'
owner.update({'C50':'J5','C51':'J5','D10':'J5','D11':'J4','D12':'J4','D13':'J4','R64':'U2','SW4':'J7','SW2':'U1','SW3':'U1','D18':'J6','D19':'J6','D20':'J7','D21':'J7','D5':'J1','D6':'J2','D7':'J2','D8':'J3','D9':'J3','D1':'J1','D2':'J2','D3':'J3','F1':'J1','F2':'J2','F3':'J3','D4':'U3','D14':'U11','D15':'U14','D16':'U14','D17':'U14','Q1':'U10','Q2':'U10','Q3':'U10','Q4':'U10','Q5':'U9','Q6':'U9','Q7':'U13'})
remaining=[r for r in by if r not in placed]
priority=['C11','C12','C81','C82','C83','C84','C90','C91','C92','C93','C94','C95','C96','C97','C98','C99','C106','C107','C108','C109','C52','C53','C34','C35','C36','C37','C38','C70','C71','C103','C104','C105','R90','R91','R92','R93','C10','R10','R11','R12','R13','R14','R15','R16','R60','R61','R50','C50','C51','D10']
remaining.sort(key=lambda r:(priority.index(r)if r in priority else len(priority),-((by[r]['bbox']['maxX']-by[r]['bbox']['minX'])*(by[r]['bbox']['maxY']-by[r]['bbox']['minY']))))
def pinpoint(ref,num):
 c=by[ref];p=next(p for p in c['pads']if p['number']==num);x,y,r=placed[ref];a=math.radians(r-c['rotation']);dx=(p['x']-c['x'])*.0254;dy=(p['y']-c['y'])*.0254;return x+dx*math.cos(a)-dy*math.sin(a),y+dx*math.sin(a)+dy*math.cos(a)
pt={}
for ref in ['C11','C12']:pt[ref]=pinpoint('U1','2')
for ref in ['C81','C82','C83','C84']:pt[ref]=pinpoint('U2','42')
for ref in ['C90','C91']:pt[ref]=pinpoint('U4','3')
pt['C92']=pinpoint('U4','6')
for ref in ['C93','C94']:pt[ref]=pinpoint('L1','2')
for ref in ['C95','R90','R91']:pt[ref]=pinpoint('U4','1')
for ref in ['C96','C106']:pt[ref]=pinpoint('U5','3')
pt['C97']=pinpoint('U5','6')
for ref in ['C98','C99']:pt[ref]=pinpoint('L2','2')
pt['C107']=pinpoint('L3','1');pt['C108']=pinpoint('D14','1')
for ref in ['C109','R92','R93']:pt[ref]=pinpoint('U11','3')
for ref in ['C52','C53']:pt[ref]=pinpoint('J4','C1')
for ref in ['R50','C50','C51','D10']:pt[ref]=pinpoint('J5','2')
for ref,pin in {'C10':'3','R10':'3','R11':'15','R12':'27','R13':'18','R14':'12','R15':'14','R16':'13'}.items():pt[ref]=pinpoint('U1',pin)
for ref,pin in {'R60':'59','R61':'60'}.items():pt[ref]=pinpoint('U2',pin)
for ref,root,pin in [('C34','U7','15'),('C35','U6','8'),('C36','U8','16'),('C37','U8','1'),('C38','U12','5'),('C70','U10','16'),('C71','U10','15'),('C103','U13','16'),('C104','U9','16'),('C105','U14','3')]:pt[ref]=pinpoint(root,pin)
grid=[(x*.4,y*.4)for x in range(2,int(W/.4)-1)for y in range(2,int(H/.4)-1)]
for ref in remaining:
 root=owner.get(ref);tx,ty=pt[ref]if ref in pt else placed[root][:2]if root in placed else targets[meta[ref]['page']];candidates=sorted(grid,key=lambda p:(p[0]-tx)**2+(p[1]-ty)**2)
 found=None
 for x,y in candidates:
  for r in [0,90]:
   b=box(ref,x,y,r)
   if valid(ref,b):found=(x,y,r,b);break
  if found:break
 if not found:fail.append(ref);continue
 x,y,r,b=found;placed[ref]=[x,y,r];bboxes[ref]=b
plan={'widthMm':W,'heightMm':H,'phase':'initial placement; routing pending','positions':{r:{'xMm':v[0],'yMm':v[1],'rotation':v[2],'bboxMm':bboxes[r],'owner':owner.get(r)}for r,v in placed.items()},'unplaced':fail};(P/'manifests/pcb-layout-plan-v04.json').write_text(json.dumps(plan,indent=2),encoding='utf-8');print('placed',len(placed),'unplaced',fail)
guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");'
arr=[{'ref':r,'x':v[0]/.0254,'y':v[1]/.0254,'rotation':v[2]}for r,v in placed.items()]
for i in range(0,len(arr),12):
 code=guard+'const specs='+json.dumps(arr[i:i+12])+';const cs=await eda.pcb_PrimitiveComponent.getAll();const out=[];for(const z of specs){const c=cs.find(c=>c.getState_Designator()===z.ref);if(!c)throw Error("Missing "+z.ref);await eda.pcb_PrimitiveComponent.modify(c,{x:z.x,y:z.y,rotation:z.rotation});out.push(z.ref);}return {placed:out,saved:await eda.pcb_Document.save()};';(P/f'scripts/layout-pcb-v04-{i//12+1}.js').write_text(code,encoding='utf-8')




