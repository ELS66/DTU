"""Compare the exact publicly loaded DFM mesh with lands and manufacturer nominal metal."""
from pathlib import Path
import sys,json,zipfile,collections,math
sys.path.insert(0,str(Path('PCB/.tools').resolve()))
from shapely.geometry import Polygon,box,Point
from shapely.affinity import rotate,translate
from shapely.ops import unary_union
R=Path('PCB');M=R/'manifests'
verts=[];faces=[];mat=None
for l in (R/'references/dfm-models/6367ea27a5384112840465ad6d260e03.obj').read_text(encoding='utf8').splitlines():
 p=l.split()
 if not p:continue
 if p[0]=='v':verts.append(tuple(map(float,p[1:4])))
 elif p[0]=='usemtl':mat=p[1]
 elif p[0]=='f':faces.append((mat,[int(x.split('/')[0])-1 for x in p[1:]]))
low=min(v[2] for v in verts)
bottom=unary_union([Polygon([verts[i][:2] for i in ids]) for mat,ids in faces if mat=='1' and all(abs(verts[i][2]-low)<1e-6 for i in ids)])
gs=list(bottom.geoms) if hasattr(bottom,'geoms') else [bottom]
s=(R/'scripts/package-silkclean-v13.py').read_text(encoding='utf8');exec(s[s.index('def active_project('):s.index('oldproj=active_project(')])
a=active_project(R/'eda/DTU-V0.14.2-60x75-Pinfix.epro2');fp='6b69a40d60760f97'
ps=[]
for k,p in a.items():
 if k[:3]!=('FOOTPRINT',fp,'PAD'):continue
 d=p['defaultPad'];g=translate(rotate(box(-d['width']*.0254/2,-d['height']*.0254/2,d['width']*.0254/2,d['height']*.0254/2),p['padAngle'],origin=(0,0)),p['centerX']*.0254,p['centerY']*.0254);ps.append((p['num'],g))
physical={r['pin']:r for r in json.loads((M/'u2-ml307-physical-reference-review-v13.json').read_text(encoding='utf8'))['physicalPads']}
rows=[]
for g in gs:
 if g.area<.001:continue
 num,land=min(ps,key=lambda pp:pp[1].centroid.distance(g.centroid));metal=box(*physical[num]['manufacturerNominalPhysicalBoundsMm'])
 rows.append({'pin':num,'dfmModelBoundsMm':list(g.bounds),'landBoundsMm':list(land.bounds),'manufacturerNominalMetalBoundsMm':list(metal.bounds),'modelOutsideCopperAreaMm2':g.difference(land).area,'maximumOverhangMm':max(Point(pt).distance(land) for pt in g.exterior.coords),'modelToManufacturerHausdorffMm':g.hausdorff_distance(metal),'modelAreaMm2':g.area})
report={'sourceUrl':'https://modules.lceda.cn/3dmodel/6367ea27a5384112840465ad6d260e03','matchedLCSC':'C48982537','publicPackageUuid':'2e739451f60d4693986b4bd55cd7f7f9','modelFootprintName':'LCC-LGA-109_L17.7-W15.8-P1.10_MC661','minimumMeshZ':low,'bottomMetalRegions':len(rows),'outsideCopper':sum(r['modelOutsideCopperAreaMm2']>1e-10 for r in rows),'outsideHistogram':dict(collections.Counter(str(round(r['maximumOverhangMm'],4)) for r in rows if r['modelOutsideCopperAreaMm2']>1e-10)),'rows':rows}
(M/'u2-dfm-actual-model-audit-v14_3.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2));print(rows[:3])
