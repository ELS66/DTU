from pathlib import Path
p=Path('PCB/scripts/prepare-pcb-layout-v04.py');s=p.read_text(encoding='utf-8-sig');s=s.replace("'U1':(13,48,0)","'U1':(14,48,0)").replace("'J4':(8,28,0)","'J4':(8,28,270)").replace("'J6':(54.7,11,90)","'J6':(5.3,63,270)")
s=s.replace("remaining.sort(key=lambda r:((by[r]['bbox']['maxX']-by[r]['bbox']['minX'])*(by[r]['bbox']['maxY']-by[r]['bbox']['minY'])),reverse=True)",'''priority=['C11','C12','C81','C82','C83','C84','C90','C91','C92','C93','C94','C95','C96','C97','C98','C99','C106','C107','C108','C109','C52','C53','C34','C35','C36','C37','C38','C70','C71','C103','C104','C105','R90','R91','R92','R93','C10','R10','R11','R12','R13','R14','R15','R16','R60','R61','R50','C50','C51','D10']
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
for ref in ['C107','C108','C109','R92','R93']:pt[ref]=pinpoint('U11','3')
for ref in ['C52','C53']:pt[ref]=pinpoint('J4','C1')
for ref in ['R50','C50','C51','D10']:pt[ref]=pinpoint('J5','2')
for ref,pin in {'C10':'3','R10':'3','R11':'15','R12':'27','R13':'18','R14':'12','R15':'14','R16':'13'}.items():pt[ref]=pinpoint('U1',pin)
for ref,pin in {'R60':'59','R61':'60'}.items():pt[ref]=pinpoint('U2',pin)
for ref,root,pin in [('C34','U7','15'),('C35','U6','8'),('C36','U8','16'),('C37','U8','1'),('C38','U12','5'),('C70','U10','16'),('C71','U10','15'),('C103','U13','16'),('C104','U9','16'),('C105','U14','3')]:pt[ref]=pinpoint(root,pin)''')
s=s.replace("root=owner.get(ref);tx,ty=placed[root][:2]if root in placed else targets[meta[ref]['page']];candidates=sorted(grid", "root=owner.get(ref);tx,ty=pt[ref]if ref in pt else placed[root][:2]if root in placed else targets[meta[ref]['page']];candidates=sorted(grid")
p.write_text(s,encoding='utf-8')
