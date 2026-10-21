from pathlib import Path
import json,math,collections,zipfile
P=Path('PCB')
exec((P/'scripts/render-routing-opt-gerber-v13.py').read_text(encoding='utf-8-sig').split('for label,copper,mask,silk in')[0])
drillsets={'PTH':drill('Drill_PTH_Through.DRL'),'NPTH':drill('Drill_NPTH_Through.DRL')}
allholes=drillsets['PTH']+drillsets['NPTH'];mind=100;pair=None
for i,a in enumerate(allholes):
 for b in allholes[:i]:
  d=math.dist(a[:2],b[:2])-(a[2]+b[2])/2
  if d<mind:mind=d;pair=[a,b]
assert len(allholes)==326 and len(drillsets['PTH'])==320 and len(drillsets['NPTH'])==6
mask=unary_union([g for g,dark in geom('Gerber_TopSolderMaskLayer.GTS')[0] if dark]);silk=unary_union([g for g,dark in geom('Gerber_TopSilkscreenLayer.GTO')[0] if dark]);silkclear=mask.distance(silk)
assert mind>.25 and silkclear>.15
files=['Gerber_TopLayer.GTL','Gerber_BottomLayer.GBL','Gerber_InnerLayer1.G1','Gerber_InnerLayer2.G2','Gerber_TopSilkscreenLayer.GTO','Gerber_BottomSilkscreenLayer.GBO','Gerber_TopSolderMaskLayer.GTS','Gerber_BottomSolderMaskLayer.GBS','Gerber_TopPasteMaskLayer.GTP','Gerber_BoardOutlineLayer.GKO','Drill_PTH_Through.DRL','Drill_NPTH_Through.DRL']
for n in files:assert n in z.namelist()
assert len(geom('Gerber_InnerLayer1.G1')[0])>0 and len(geom('Gerber_InnerLayer2.G2')[0])>0
assert 'Gerber_BottomPasteMaskLayer.GBP' not in z.namelist()
target=P/'eda/DTU-V0.13-60x70-routing-optimized-Gerber.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as out:
 for n in files:out.writestr(n,z.read(n))
result={'totalDrilledHoles':len(allholes),'PTH':len(drillsets['PTH']),'NPTH':len(drillsets['NPTH']),'drillDiameters':dict(collections.Counter(round(h[2],3) for h in allholes)),'minimumDrillWallGapMm':mind,'closestDrills':pair,'topSilkMaskClearanceMm':silkclear,'manufacturingFileCount':len(files),'removedDuplicateViaDrill':True,'copperLayers':4,'assemblySide':'Top only','factoryDFM':'Pending'}
(P/'manifests/routing-opt-manufacturing-check-v13.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
