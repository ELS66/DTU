from pathlib import Path
import json,zipfile,math,re,collections
R=Path('PCB');M=R/'manifests';E=R/'eda'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2),encoding='utf8')
s=(R/'scripts/package-silkclean-v13.py').read_text(encoding='utf8');exec(s[s.index('def rows('):s.index('before=rows(')])
after=rows(load(M/'clearancefix-final-source-v14.json')['result']['source']);plan=load(M/'clearancefix-actual-routing-v14.json')
exec((R/'scripts/render-hy20-gerber-v13.py').read_text(encoding='utf8').split('for label,copper,mask,silk in')[0])
from shapely.strtree import STRtree
from shapely.affinity import rotate,translate
z.close();z=zipfile.ZipFile(E/'DTU-V0.14-60x75-Clearancefix-Gerber-raw');cache.clear();npth=drill('Drill_NPTH_Through.DRL');mounts=[q for q in npth if q[2]>3]
assert len(mounts)==4
for xy in [(4,4),(56,4),(4,71),(56,71)]:assert any(math.dist(xy,q[:2])<.00001 and abs(q[2]-3.2)<1e-6 for q in mounts)
# The native exporter adds zero-size NPTH copper placeholders and tiny tented-via mask flashes.
# Retain the established cleanup with identity checks against native drill/via data.
s=(R/'scripts/package-exposurefix-v13.py').read_text(encoding='utf8');segment=s[s.index('layers='):s.index('mask=unary_union')].replace('Exposurefix-Gerber.zip','Clearancefix-Gerber.zip').replace('DTU-V0.13-60x70-Clearancefix','DTU-V0.14-60x75-Clearancefix');exec(segment)
pth=drill('Drill_PTH_Through.DRL');npth=drill('Drill_NPTH_Through.DRL');holes=pth+npth
assert len(pth)==320 and len(npth)==6 and len(holes)==326
gap=min(math.dist(a[:2],b[:2])-(a[2]+b[2])/2 for i,a in enumerate(holes) for b in holes[:i]);assert gap>=.3
mask=unary_union([g for g,d in geom('Gerber_TopSolderMaskLayer.GTS')[0] if d]);silk=unary_union([g for g,d in geom('Gerber_TopSilkscreenLayer.GTO')[0] if d])
silkhole=min(silk.distance(Point(x,y).buffer(di/2)) for x,y,di in holes);silkmask=silk.distance(mask)
assert silkhole>.25 and silkmask>.25
old=zipfile.ZipFile(E/'DTU-V0.13-60x70-ML307fix-Gerber.zip')
new_silk=geom('Gerber_TopSilkscreenLayer.GTO')[0];production_zip=z;z=old;cache.clear();old_silk=geom('Gerber_TopSilkscreenLayer.GTO')[0];z=production_zip;cache.clear()
assert len(new_silk)==len(old_silk)
tree=STRtree([g for g,d in old_silk]);used=set()
for g,dark in new_silk:
 candidates=[int(i) for i in tree.query(g.representative_point().buffer(.00002)) if int(i) not in used and old_silk[i][1]==dark and g.hausdorff_distance(old_silk[i][0])<.00001]
 assert candidates,('Silkscreen geometry changed',g.bounds)
 used.add(candidates[0])
assert not geom('Gerber_BottomSilkscreenLayer.GBO')[0]
outline=unary_union([g for g,d in geom('Gerber_BoardOutlineLayer.GKO')[0] if d]);assert max(abs(x-y) for x,y in zip(outline.bounds,[-.05,-.05,60.05,75.05]))<.00001,outline.bounds
# All moved upper-board via annuli must remain covered away from mask openings.
before=load(M/'ml307fix-actual-routing-v13.json');oldvias={v['id']:v for v in before['vias']};via_checks=[]
for v in plan['vias']:
 oldv=oldvias.get(v['id'])
 if oldv is not None and math.dist((v['x'],v['y']),(oldv['x'],oldv['y']))<.0001:continue
 pt=Point(v['x'],v['y']);d=pt.buffer(v['diameter']/2).distance(mask)
 via_checks.append({'via':v['id'],'net':v['net'],'annulusToMaskGapMm':d,'holeToMaskGapMm':pt.buffer(v['hole']/2).distance(mask)})
 assert d>=.15,(v['id'],d)
rf=[r for r in plan['routes'] if r['net'] in ['LTE_ANT','LTE_RF_FEED']];assert all(r['layer']==1 and abs(r['widthMm']-.35)<1e-5 for r in rf)
assert not any(v['net'] in ['LTE_ANT','LTE_RF_FEED'] for v in plan['vias'])
fpcheck=load(M/'clearancefix-footprint-audit-v14.json');report={'boardMm':[60,75],'copperLayers':4,'gerberFiles':len(z.namelist()),'viaCount':len(plan['vias']),'drillCount':len(holes),'mountsNPTHMm':mounts,'minimumDrillWallGapMm':gap,'silkToDrillWallMinimumGapMm':silkhole,'silkToMaskMinimumGapMm':silkmask,'silkscreenGeometryUnchanged':True,'minimumMovedViaAnnulusToMaskGapMm':min(q['annulusToMaskGapMm'] for q in via_checks),'upperViaChecks':via_checks,'rfAllTopNoSignalVias':True,'physicalLeadCopperContainmentCount':fpcheck['copperContainsNominalLeadCount'],'unchangedNominalPasteAperturesCount':fpcheck['pasteAperturesMatchOriginalNominalCount'],'nominalLeadCopperMinimumMarginMm':fpcheck['minimumNominalLeadCopperMarginMm'],'removedZeroSizeMountCopperPlaceholders':removed_mounts,'removedNumericalMaskResidues':len(mask_residues),'factoryDfmPassed':False}
save(M/'clearancefix-manufacturing-verification-v14.json',report)
# Actual production Gerber preview, overlaid with unchanged library body outlines at new positions.
bodies=load(M/'clearancefix-final-body-audit-v14.json')['bounds'];default={q['Designator'] for q in __import__('csv').DictReader((E/'DTU-V0.14-Clearancefix-BOM-99.csv').open(encoding='utf-8-sig'))}
for detail in [False,True]:
 xb,yb,xe,ye=(5,43,29,72) if detail else (0,0,60,75);scale=44 if detail else 20
 im=Image.new('RGB',(int((xe-xb)*scale)+80,int((ye-yb)*scale)+110),'#f5f7f6');d=ImageDraw.Draw(im);xy=lambda x,y:(40+(x-xb)*scale,60+(ye-y)*scale);d.rectangle([xy(xb,ye),xy(xe,yb)],fill='#18382e')
 for name,color in [('Gerber_TopLayer.GTL','#527565'),('Gerber_TopSolderMaskLayer.GTS','#ddc785'),('Gerber_TopSilkscreenLayer.GTO','#fffef4')]:
  for g,dark in geom(name)[0]:draw_geom(d,g.intersection(box(xb,yb,xe,ye)),color if dark else '#18382e',xy)
 for ref,b in bodies.items():
  if ref not in default or b[2]<xb or b[0]>xe or b[3]<yb or b[1]>ye:continue
  p0=xy(max(xb,b[0]),min(ye,b[3]));p1=xy(min(xe,b[2]),max(yb,b[1]));d.rectangle([p0,p1],outline='#a4b9ad' if ref not in ['U1','U2'] else '#e5e9dd',width=1)
  if ref in ['U1','U2']:d.text((p0[0]+8,p0[1]+8),'ML307R-DL' if ref=='U2' else 'ESP32-C5',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19),fill='#ffffff')
 for x,y,di in holes:
  if xb<=x<=xe and yb<=y<=ye:
   px,py=xy(x,y);rr=di*scale/2;d.ellipse((px-rr,py-rr,px+rr,py+rr),fill='#07160e')
 d.text((40,17),'V0.14 / 60 x 75 mm / 4 layers / Top assembly',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22),fill='#18382e')
 d.text((40,im.height-32),'Native exported Gerber + library body outlines; factory DFM pending.',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16),fill='#18382e')
 im.save(E/('DTU-V0.14-Clearancefix-ML307-detail.png' if detail else 'DTU-V0.14-Clearancefix-preview.png'))
print(json.dumps({k:v for k,v in report.items() if k!='upperViaChecks'},ensure_ascii=True))
