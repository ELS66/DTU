"""Regression guard: mounting-hole keepouts must follow hole centers on both inner layers."""
from pathlib import Path
import json,zipfile,math,collections
R=Path('PCB');M=R/'manifests';E=R/'eda'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
s=(R/'scripts/package-silkclean-v13.py').read_text(encoding='utf8');exec(s[s.index('def rows('):s.index('before=rows(')]);exec(s[s.index('def active_project('):s.index('oldproj=active_project(')])
stage=load(M/'mountfix-plan-v14_1.json');before=rows(load(M/'mounts-audit-live-source-v14.json')['result']['source']);after=rows(load(M/'mountfix-source-v14_1.json')['result']['source']);moves={v['id']:v for v in stage['regionMoves']}
changes=[k for k in before.keys()|after.keys() if before.get(k)!=after.get(k)]
assert {k[1] for k in changes if k[0]=='REGION'}==set(moves)
assert all(k[0] in ['REGION','POURED'] for k in changes),changes
for i,m in moves.items():
 a,b=before[('REGION',i)],after[('REGION',i)]
 assert all(a.get(k)==b.get(k) for k in a.keys()|b.keys() if k!='path')
 assert len(b['path'])==1 and len(b['path'][0])==len(m['newPath'])
 assert all(x==y if isinstance(x,str) else abs(x-y)<.0001 for x,y in zip(b['path'][0],m['newPath']))
assert load(M/'mountfix-drc-v14_1.json')['result']==[]
a=active_project(Path(stage['baseline']['nativeProject']));b=active_project(E/'DTU-V0.14.1-60x75-Mountfix.epro2')
assert all(k[0]=='PCB' for k in a.keys()|b.keys() if a.get(k)!=b.get(k))
holes=[];region_checks=[]
for (t,i),p in after.items():
 if t=='PAD' and p.get('plated') is False and p.get('hole',{}).get('width',0)*.0254>3:
  holes.append({'id':i,'centerMm':[p['centerX']*.0254,p['centerY']*.0254],'diameterMm':p['hole']['width']*.0254})
assert len(holes)==4
for h in holes:
 for layer in [15,16]:
  candidates=[]
  for (t,i),r in after.items():
   if t!='REGION' or r['layerId']!=layer or r['prohibitType']!=['COPPER']:continue
   vs=[v*.0254 for v in r['path'][0] if isinstance(v,(int,float))];xx,yy=vs[::2],vs[1::2];center=[(min(xx)+max(xx))/2,(min(yy)+max(yy))/2]
   candidates.append((math.dist(center,h['centerMm']),i,center,(max(xx)-min(xx))/2))
  offset,i,c,radius=min(candidates);assert offset<.00001 and abs(radius-3.4)<.00001
  region_checks.append({'hole':h['id'],'layer':layer,'region':i,'holeCenterMm':h['centerMm'],'regionCenterMm':c,'centerErrorMm':offset,'nominalKeepoutRadiusMm':radius})
assert len(region_checks)==8
mount_hole_records=holes
# Reuse only the established native-export numeric cleanup; all physical holes and annuli remain.
plan=load(M/'clearancefix-actual-routing-v14.json')
exec((R/'scripts/render-hy20-gerber-v13.py').read_text(encoding='utf8').split('for label,copper,mask,silk in')[0])
from shapely.strtree import STRtree
z.close();z=zipfile.ZipFile(E/'DTU-V0.14.1-60x75-Mountfix-Gerber-raw');cache.clear();npth=drill('Drill_NPTH_Through.DRL');mounts=[q for q in npth if q[2]>3]
s=(R/'scripts/package-exposurefix-v13.py').read_text(encoding='utf8');segment=s[s.index('layers='):s.index('mask=unary_union')].replace('DTU-V0.13-60x70-Exposurefix-Gerber.zip','DTU-V0.14.1-60x75-Mountfix-Gerber.zip');exec(segment)
new=z;old=zipfile.ZipFile(stage['baseline']['productionGerber']);unchanged=[];inner=['Gerber_InnerLayer1.G1','Gerber_InnerLayer2.G2']
for name in new.namelist():
 if name in inner:continue
 if name.endswith('.DRL'):
  z=new;aa=sorted(drill(name));z=old;bb=sorted(drill(name));assert len(aa)==len(bb) and all(abs(x-y)<.00001 for p,q in zip(aa,bb) for x,y in zip(p,q)),name
 else:
  z=new;cache.clear();aa=geom(name)[0];z=old;cache.clear();bb=geom(name)[0];assert len(aa)==len(bb),(name,len(aa),len(bb))
  if aa:
   tree=STRtree([g for g,d in bb]);used=set()
   for g,d in aa:
    ii=[int(i) for i in tree.query(g.representative_point().buffer(.00002)) if int(i) not in used and bb[i][1]==d and g.hausdorff_distance(bb[i][0])<.00001];assert ii,(name,g.bounds);used.add(ii[0])
 unchanged.append(name)
assert len(unchanged)==10
# Keep the ten verified unchanged production files byte-identical to the delivered baseline.
contents={name:(old.read(name) if name in unchanged else new.read(name)) for name in new.namelist()};new.close()
production=E/'DTU-V0.14.1-60x75-Mountfix-Gerber.zip'
with zipfile.ZipFile(production,'w',zipfile.ZIP_DEFLATED) as dest:
 for name,data in contents.items():dest.writestr(name,data)
z=zipfile.ZipFile(production);cache.clear();copper_checks=[];old_copper_checks=[]
for name in ['Gerber_TopLayer.GTL','Gerber_BottomLayer.GBL']+inner:
 copper=unary_union([g for g,d in geom(name)[0] if d])
 for x,y,di in mounts:
  distance=Point(x,y).distance(copper);assert distance>=3.39,(name,x,y,distance)
  copper_checks.append({'layer':name,'holeCenterMm':[x,y],'centerToCopperMm':distance,'holeWallToCopperMm':distance-di/2})
 if name in inner:
  for x in [4,56]:
   fraction=copper.intersection(Point(x,66).buffer(.5)).area/Point(x,66).buffer(.5).area;assert fraction>.999
   old_copper_checks.append({'layer':name,'oldKeepoutCenterMm':[x,66],'oldCenterNowCopperFillFraction':fraction})
pth=drill('Drill_PTH_Through.DRL');npth=drill('Drill_NPTH_Through.DRL');assert len(pth)+len(npth)==326 and len(pth)==320 and len(npth)==6
report={'revision':'V0.14.1','boardMm':[60,75],'holesUnchanged':mount_hole_records,'regionToHoleCenterChecks':region_checks,'maximumRegionCenterErrorMm':max(r['centerErrorMm'] for r in region_checks),'sourceChanges':dict(collections.Counter(k[0] for k in changes)),'drilledHoles':326,'vias':310,'nativeDrcIssues':0,'actualFourLayerCopperClearances':copper_checks,'formerTopKeepoutsRefilled':old_copper_checks,'unchangedProductionFilesByBytes':unchanged,'changedProductionFiles':inner,'schematicComponentsAndRoutedCopperUnchanged':True,'factoryDfmPassed':False}
save(M/'mountfix-verification-v14_1.json',report)
# Before/after crops are taken from actual inner-layer exports, shown from the top.
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20);im=Image.new('RGB',(1160,1060),'#f4f6f5');d=ImageDraw.Draw(im);d.text((30,15),'V0.14.1 / top mounting holes / actual L2 copper',font=font,fill='#18382e')
for row,cx in enumerate([4,56]):
 for col,(label,archive) in enumerate([('BEFORE / V0.14',old),('AFTER / V0.14.1',z)]):
  ox=30+col*570;oy=70+row*490;xb=cx-4;yb=62;xe=cx+6;ye=75;scale=31
  xy=lambda x,y:(ox+90+(x-xb)*scale,oy+35+(ye-y)*scale)
  d.text((ox+70,oy),label+(' / LEFT' if row==0 else ' / RIGHT'),font=font,fill='#18382e')
  d.rectangle([xy(xb,ye),xy(xe,yb)],fill='#17372d')
  zsave=z;z=archive;cache.clear()
  for g,dark in geom('Gerber_InnerLayer1.G1')[0]:draw_geom(d,g.intersection(box(xb,yb,xe,ye)),'#c7aa5d' if dark else '#17372d',xy)
  z=zsave;cache.clear()
  px,py=xy(cx,71);rr=1.6*scale;d.ellipse((px-rr,py-rr,px+rr,py+rr),fill='#080e0c',outline='#eeeeee',width=2);d.line((px-9,py,px+9,py),fill='#e96559',width=2);d.line((px,py-9,px,py+9),fill='#e96559',width=2)
  kx,ky=xy(cx,66 if col==0 else 71);kr=3.4*scale;d.ellipse((kx-kr,ky-kr,kx+kr,ky+kr),outline='#679de1',width=2)
d.text((30,1030),'Blue outline: source keepout boundary. Red cross: actual drill center.',font=font,fill='#18382e')
im.save(E/'DTU-V0.14.1-Mountfix-before-after.png')
print(json.dumps({k:v for k,v in report.items() if k not in ['actualFourLayerCopperClearances','regionToHoleCenterChecks','holesUnchanged']},ensure_ascii=True))
