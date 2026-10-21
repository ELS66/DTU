"""Verify two relocated lead-adjacent vias and package current native Gerbers."""
from pathlib import Path
import json,zipfile,re,math,collections,shutil,hashlib
R=Path('PCB');M=R/'manifests';E=R/'eda';D=R/'docs'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
code=(R/'scripts/package-silkclean-v13.py').read_text(encoding='utf8');exec(code[code.index('def rows('):code.index('before=rows(')])
before=rows(load(M/'lead-hole-before-source-v13.json')['result']['source']);after=rows(load(M/'lead-hole-reopened-source-v13.json')['result']['source']);changes=load(M/'lead-hole-proposed-changes-v13.json');plan=load(M/'lead-hole-actual-routing-v13.json')
changed=[k for k in before.keys()|after.keys() if before.get(k)!=after.get(k)]
assert collections.Counter(k[0] for k in changed)=={'VIA':2,'POLY':7,'POURED':3}
assert {k[1] for k in changed if k[0]=='VIA'}=={q['id'] for q in changes['movedVias']}
assert {k[1] for k in changed if k[0]=='POLY'}=={q['id'] for q in changes['updatedRoutes']}|set(changes['deleteRoutes'])
for k in changed:
 if k[0]=='VIA':assert all(before[k].get(f)==after[k].get(f) for f in before[k].keys()|after[k].keys() if f not in ['centerX','centerY'])
assert load(M/'lead-hole-drc-v13.json')['result']==[]
exec((R/'scripts/render-hy20-gerber-v13.py').read_text(encoding='utf8').split('for label,copper,mask,silk in')[0])
z.close();z=zipfile.ZipFile(E/'DTU-V0.13-60x70-Leadholefix-Gerber-raw');cache.clear();npth=drill('Drill_NPTH_Through.DRL');mounts=[q for q in npth if q[2]>3]
# Preserve the established handling of zero-diameter NPTH placeholder copper and nanometre mask residues.
clean=(R/'scripts/package-exposurefix-v13.py').read_text(encoding='utf8');segment=clean[clean.index('layers='):clean.index('mask=unary_union')].replace('Exposurefix-Gerber.zip','Leadholefix-Gerber.zip');exec(segment)
production=E/'DTU-V0.13-60x70-Leadholefix-Gerber.zip';new=z;old=zipfile.ZipFile(E/'DTU-V0.13-60x70-Silkholefix-Gerber.zip')
# Only copper and PTH drills should change; all remaining production layers are compared geometrically.
nonchanged=[n for n in old.namelist() if n not in layers+['Drill_PTH_Through.DRL']]
from shapely.strtree import STRtree
for name in nonchanged:
 if name.endswith('.DRL'):
  z=new;aa=sorted(drill(name));z=old;bb=sorted(drill(name));assert len(aa)==len(bb) and all(max(abs(x-y) for x,y in zip(a,b))<.00001 for a,b in zip(aa,bb));continue
 z=new;cache.clear();a=geom(name)[0];z=old;cache.clear();b=geom(name)[0];assert len(a)==len(b),(name,len(a),len(b))
 if a:
  index=STRtree([g for g,d in b]);used=set()
  for g,d in a:
   options=[int(i) for i in index.query(g.representative_point().buffer(.00002)) if int(i) not in used and b[i][1]==d and g.hausdorff_distance(b[i][0])<.00001]
   assert options,(name,g.bounds);used.add(options[0])
# Leave unchanged manufacturing layers byte-identical to the previous production ZIP.
contents={n:old.read(n) if n in nonchanged else new.read(n) for n in old.namelist()};new.close()
with zipfile.ZipFile(production,'w',zipfile.ZIP_DEFLATED) as q:
 for n,v in contents.items():q.writestr(n,v)
z=zipfile.ZipFile(production);cache.clear();holes=drill('Drill_PTH_Through.DRL')+drill('Drill_NPTH_Through.DRL');assert len(holes)==322
mask=unary_union([g for g,d in geom('Gerber_TopSolderMaskLayer.GTS')[0] if d]);silk=unary_union([g for g,d in geom('Gerber_TopSilkscreenLayer.GTO')[0] if d]);silkhole=min(silk.distance(Point(x,y).buffer(di/2)) for x,y,di in holes);assert silkhole>.25 and silk.distance(mask)>.25
holegap=min(math.hypot(a[0]-b[0],a[1]-b[1])-(a[2]+b[2])/2 for i,a in enumerate(holes) for b in holes[:i]);assert holegap>.25
model=load(M/'lead-hole-model-pairs-v13.json');moved=[]
for v in changes['movedVias']:
 q=next(q for q in plan['vias'] if q['id']==v['id']);records=[r for r in model if r['via']['id']==v['id']];lead=unary_union([box(*r['leadBoundsMm']) for r in records]);hole=Point(q['x'],q['y']).buffer(q['hole']/2);ann=Point(q['x'],q['y']).buffer(q['diameter']/2)
 leadgap=lead.distance(hole);assert leadgap>=.3 and ann.distance(mask)>.15
 assert any(math.dist(v['to'],h[:2])<.00001 and abs(h[2]-.2)<.00001 for h in holes)
 assert not any(math.dist(v['from'],h[:2])<.00001 for h in holes)
 moved.append({'via':v['id'],'net':q['net'],'fromMm':v['from'],'toMm':v['to'],'modelLeadToHoleGapMm':leadgap,'annulusToMaskGapMm':ann.distance(mask),'holeToMaskGapMm':hole.distance(mask)})
verification={'PCB_DRC':0,'factoryDfmPassed':False,'movedVias':moved,'routes':len(plan['routes']),'vias':len(plan['vias']),'drills':len(holes),'minimumDrillWallGapMm':holegap,'silkToDrillWallMinimumGapMm':silkhole,'silkToMaskMinimumGapMm':silk.distance(mask),'unchangedProductionFilesByBytes':nonchanged,'nativeNonChangedGerberGeometryCompared':True,'changedSourceTypes':dict(collections.Counter(k[0] for k in changed)),'componentPadNetTextRulesUnchanged':True,'BOMandCPLUnchanged':True,'localModelLimitations':'DFM may use different lead models; four screenshots rows match two locations but factory rerun is required. J4 other ground-lead model has existing ~0.125mm hole clearance, not matched to displayed 0.02mm pairs; remains to confirm.','independentCopperCheck':'No new conflicts; 2 existing nonedited pair distances about0.151961mm vs helper0.1528mm threshold are retained and nativeDRC0.'}
save(M/'leadholefix-manufacturing-verification-v13.json',verification)
# Engineering closeups rendered from actual output.
for ref,win in [('Q1',(25.5,39.5,30,44)),('J4',(18,23.5,24.5,29))]:
 xb,yb,xe,ye=win;scale=100;im=Image.new('RGB',(int((xe-xb)*scale)+60,int((ye-yb)*scale)+90),'#f4f6f5');d=ImageDraw.Draw(im);xy=lambda x,y:(30+(x-xb)*scale,60+(ye-y)*scale);d.rectangle([xy(xb,ye),xy(xe,yb)],fill='#15382e')
 for n,c in [('Gerber_TopLayer.GTL','#477662'),('Gerber_TopSolderMaskLayer.GTS','#d2b866'),('Gerber_TopSilkscreenLayer.GTO','#fffde8')]:
  for g,dark in geom(n)[0]:draw_geom(d,g.intersection(box(*win)),c if dark else '#15382e',xy)
 for x,y,di in holes:
  if xb<=x<=xe and yb<=y<=ye:
   px,py=xy(x,y);r=di*scale/2;d.ellipse((px-r,py-r,px+r,py+r),fill='#000000')
 for v in moved:
  x,y=v['toMm']
  if xb<=x<=xe and yb<=y<=ye:
   px,py=xy(x,y);d.ellipse((px-30,py-30,px+30,py+30),outline='#65e8ff',width=3)
 d.text((30,16),ref+' / Leadholefix / moved via marked cyan',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18),fill='#18372e');im.save(E/f'DTU-V0.13-Leadholefix-{ref}-detail.png')
print(json.dumps(verification,ensure_ascii=True))
