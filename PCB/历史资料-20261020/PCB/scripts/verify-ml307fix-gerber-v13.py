"""Validate exported land patterns and retain prior drill/NPTH manufacturing cleanup."""
from pathlib import Path
import json,zipfile,re,math,collections
R=Path('PCB');M=R/'manifests';E=R/'eda'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
code=(R/'scripts/package-silkclean-v13.py').read_text(encoding='utf8');exec(code[code.index('def rows('):code.index('before=rows(')]);exec(code[code.index('def active_project('):code.index('oldproj=active_project(')])
a=active_project(E/'DTU-V0.13-60x70-ML307fix.epro2');after=rows(load(M/'ml307fix-reopened-source-v13.json')['result']['source']);plan=load(M/'ml307fix-actual-routing-v13.json')
exec((R/'scripts/render-hy20-gerber-v13.py').read_text(encoding='utf8').split('for label,copper,mask,silk in')[0])
z.close();z=zipfile.ZipFile(E/'DTU-V0.13-60x70-ML307fix-Gerber-raw');cache.clear();npth=drill('Drill_NPTH_Through.DRL');mounts=[q for q in npth if q[2]>3]
clean=(R/'scripts/package-exposurefix-v13.py').read_text(encoding='utf8');segment=clean[clean.index('layers='):clean.index('mask=unary_union')].replace('Exposurefix-Gerber.zip','ML307fix-Gerber.zip');exec(segment)
production=E/'DTU-V0.13-60x70-ML307fix-Gerber.zip';new=z;old=zipfile.ZipFile(E/'DTU-V0.13-60x70-Leadholefix-Gerber.zip')
nonchanged=['Gerber_TopSilkscreenLayer.GTO','Gerber_BottomSilkscreenLayer.GBO','Gerber_BottomSolderMaskLayer.GBS','Gerber_BoardOutlineLayer.GKO','Drill_NPTH_Through.DRL']
from shapely.strtree import STRtree
for name in nonchanged:
 if name.endswith('.DRL'):
  z=new;aa=sorted(drill(name));z=old;bb=sorted(drill(name));assert len(aa)==len(bb) and all(max(abs(x-y) for x,y in zip(a,b))<.00001 for a,b in zip(aa,bb));continue
 z=new;cache.clear();aa=geom(name)[0];z=old;cache.clear();bb=geom(name)[0];assert len(aa)==len(bb),(name,len(aa),len(bb))
 if aa:
  index=STRtree([g for g,d in bb]);used=set()
  for g,d in aa:
   options=[int(i) for i in index.query(g.representative_point().buffer(.00002)) if int(i) not in used and bb[i][1]==d and g.hausdorff_distance(bb[i][0])<.00001];assert options,(name,g.bounds);used.add(options[0])
contents={n:old.read(n) if n in nonchanged else new.read(n) for n in old.namelist()};new.close()
with zipfile.ZipFile(production,'w',zipfile.ZIP_DEFLATED) as q:
 for n,v in contents.items():q.writestr(n,v)
z=zipfile.ZipFile(production);cache.clear();pth=drill('Drill_PTH_Through.DRL');npth=drill('Drill_NPTH_Through.DRL');holes=pth+npth;assert len(pth)==318 and len(npth)==6 and len(holes)==324
holegap=min(math.dist(a[:2],b[:2])-(a[2]+b[2])/2 for i,a in enumerate(holes) for b in holes[:i]);assert holegap>.25,holegap
mask=unary_union([g for g,d in geom('Gerber_TopSolderMaskLayer.GTS')[0] if d]);silk=unary_union([g for g,d in geom('Gerber_TopSilkscreenLayer.GTO')[0] if d]);silkhole=min(silk.distance(Point(x,y).buffer(di/2)) for x,y,di in holes);silkmask=silk.distance(mask);assert silkhole>.25 and silkmask>.25
# Reconstruct the intended capsule from exact native source and compare actual copper/mask/paste flashes.
from shapely.affinity import rotate,translate
comp=after[('COMPONENT','9a20c59b6357d964')];fp='6b69a40d60760f97';nativepads=[(k,b) for k,b in a.items() if k[:3]==('FOOTPRINT',fp,'PAD')];matches=[]
feature_sets={name:[g for g,d in geom(name)[0] if d] for name in ['Gerber_TopLayer.GTL','Gerber_TopSolderMaskLayer.GTS','Gerber_TopPasteMaskLayer.GTP']};indices={n:STRtree(gs) for n,gs in feature_sets.items()}
for k,p in nativepads:
 if p['defaultPad']['width']*.0254<2.5:continue
 g=LineString([(-1,0),(1,0)]).buffer(.3);g=translate(rotate(g,p['padAngle'],origin=(0,0)),p['centerX']*.0254,p['centerY']*.0254);g=translate(rotate(g,comp['angle'],origin=(0,0)),comp['x']*.0254,comp['y']*.0254)
 row={'pin':p['num'],'copperBoundsMm':list(g.bounds)}
 for name,gs in feature_sets.items():
  cand=[int(i) for i in indices[name].query(g.centroid.buffer(.01))];best=min((gs[i].hausdorff_distance(g),i) for i in cand)
  if name=='Gerber_TopLayer.GTL' or name=='Gerber_TopPasteMaskLayer.GTP':assert best[0]<.00001,(name,p['num'],best[0])
  else:assert .049<best[0]<.053,(p['num'],best[0])
  row[name]=best[0]
 matches.append(row)
assert len(matches)==48
# Drill-wall clearance to all mask openings for vias moved away from the extended lands.
diff=load(M/'ml307fix-routing-diff-v13.json');moved=[]
for vid,pt in diff['viaTargets'].items():
 v=next(v for v in plan['vias'] if v['id']==vid);center=Point(v['x'],v['y']);gap=center.buffer(v['diameter']/2).distance(mask);assert gap>.15,(vid,gap)
 moved.append({'via':vid,'centerMm':pt,'annulusToMaskGapMm':gap,'holeToMaskGapMm':center.buffer(v['hole']/2).distance(mask)})
# Previous Q1/J4 lead-hole repair remains intact.
previous=load(M/'leadholefix-manufacturing-verification-v13.json')
for q in previous['movedVias']:
 v=next(v for v in plan['vias'] if v['id']==q['via']);assert math.dist((v['x'],v['y']),q['toMm'])<.00001
native=load(M/'ml307fix-native-verification-v13.json');native.update({'drills':len(holes),'minimumDrillWallGapMm':holegap,'silkToDrillWallMinimumGapMm':silkhole,'silkToMaskMinimumGapMm':silkmask,'exportedCapsulePadCountVerified':48,'exportedCopperPasteCapsuleRadiusMm':.3,'exportedTopMaskExpansionMm':.0508,'nativePadCornerRatio':100,'unchangedProductionFilesByBytes':nonchanged,'movedViaOpeningClearances':moved,'minimumMovedViaAnnulusMaskGapMm':min(v['annulusToMaskGapMm'] for v in moved),'manufacturerDfmPassed':False,'engineeringLimitations':['Manufacturer DFM and solder process confirmation remain pending.','Rounded official-style lands and physical lead heel/castellation geometry may still trigger generic PIN boundary checks; no models deleted or shrunk merely to suppress warnings.','50ohmRF/90ohmUSB impedance requires actual production stackup verification; existing0.35mmRF width retained.']})
save(M/'ml307fix-manufacturing-verification-v13.json',native);save(M/'ml307fix-exported-pad-check-v13.json',matches)
for detail in [False,True]:
 xb,yb,xe,ye=(5,58,27,68) if detail else (0,0,60,70);scale=55 if detail else 22
 im=Image.new('RGB',(int((xe-xb)*scale)+80,int((ye-yb)*scale)+100),'#f4f6f5');d=ImageDraw.Draw(im);xy=lambda x,y:(40+(x-xb)*scale,60+(ye-y)*scale);d.rectangle([xy(xb,ye),xy(xe,yb)],fill='#15382e')
 for name,color in [('Gerber_TopLayer.GTL','#426d5c'),('Gerber_TopSolderMaskLayer.GTS','#d9bf76'),('Gerber_TopSilkscreenLayer.GTO','#fffce6')]:
  for g,dark in geom(name)[0]:draw_geom(d,g.intersection(box(xb,yb,xe,ye)),color if dark else '#15382e',xy)
 for x,y,di in holes:
  if xb<=x<=xe and yb<=y<=ye:
   px,py=xy(x,y);r=di*scale/2;d.ellipse((px-r,py-r,px+r,py+r),fill='#000000')
 d.text((40,16),'ML307fix / native exported copper, mask and drill geometry',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',21),fill='#19392e');im.save(E/('DTU-V0.13-ML307fix-RF-USB-detail.png' if detail else 'DTU-V0.13-ML307fix-Gerber-preview.png'))
print(json.dumps({k:v for k,v in native.items() if k!='movedViaOpeningClearances'},ensure_ascii=True))
