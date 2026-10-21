"""Verify actual factory-loaded 3D bottom metal against newly exported copper."""
from pathlib import Path
import sys,json,zipfile,math,hashlib
sys.path.insert(0,str(Path('PCB/.tools').resolve()))
from shapely.geometry import Polygon,box,Point
from shapely.affinity import rotate,translate
from shapely.ops import unary_union
from shapely.strtree import STRtree
R=Path('PCB');M=R/'manifests';E=R/'eda'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
s=(R/'scripts/audit-dfm-u2-actual-model-v14_3.py').read_text(encoding='utf8');exec(s[:s.index("s=(R/'scripts/package-silkclean-v13.py')")])
dfm_polys=[g for g in gs if g.area>.001];assert len(dfm_polys)==109
exec((R/'scripts/render-hy20-gerber-v13.py').read_text(encoding='utf8').split('for label,copper,mask,silk in')[0])
z.close();z=zipfile.ZipFile(E/'DTU-V0.14.3-60x75-U2fix-Gerber.zip');cache.clear()
c=next(c for c in load(M/'clearancefix-final-pads-v14.json')['result'] if c['ref']=='U2')
cu=[g for g,d in geom('Gerber_TopLayer.GTL')[0] if d];tree=STRtree(cu)
masks=[g for g,d in geom('Gerber_TopSolderMaskLayer.GTS')[0] if d];mtree=STRtree(masks)
rows=[]
for g in dfm_polys:
 worldg=translate(rotate(g,c['rotation'],origin=(0,0)),c['x']*.0254,c['y']*.0254)
 hit=[cu[int(i)] for i in tree.query(worldg.centroid.buffer(.001))];assert hit
 land=unary_union(hit);outside=worldg.difference(land).area
 assert outside<1e-9,('DFM mesh outside actual copper',g.bounds,outside)
 mhit=[masks[int(i)] for i in mtree.query(worldg.centroid.buffer(.001))];assert mhit
 mask=unary_union(mhit);assert worldg.difference(mask).area<1e-9
 rows.append({'modelBoundsLocalMm':list(g.bounds),'outsideActualCopperMm2':outside,'copperMarginMm':worldg.distance(land.boundary),'solderMaskMarginMm':worldg.distance(mask.boundary)})
old=load(M/'u2-dfm-actual-model-audit-v14_3.json')
report={'modelUrl':old['sourceUrl'],'modelSha256':hashlib.sha256((R/'references/dfm-models/6367ea27a5384112840465ad6d260e03.obj').read_bytes()).hexdigest(),'sourceOfModel':'Public model URL observed in current JLC DFM cache, identified by 15.8 x 17.7mm body and 109 bottom metallic regions; matched model name confirmed by user screenshot.','regionsChecked':109,'copperContainmentPassed':109,'solderMaskContainmentPassed':109,'minimumDfmModelCopperMarginMm':min(r['copperMarginMm'] for r in rows),'minimumDfmModelMaskMarginMm':min(r['solderMaskMarginMm'] for r in rows),'factoryDfmPassed':False,'scope':'Exact downloaded bottom-metal triangles versus actual exported copper/mask. Does not reproduce the proprietary DFM edge classifier or certify real assembly tolerances.','rows':rows}
(M/'u2boundary-dfm-mesh-verification-v14_3.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='rows'},ensure_ascii=True))
