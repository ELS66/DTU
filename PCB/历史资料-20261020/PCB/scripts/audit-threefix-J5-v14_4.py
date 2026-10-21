from pathlib import Path
import json,sys,zipfile
sys.path.insert(0,str(Path('PCB/.tools').resolve()))
exec(Path('PCB/scripts/render-hy20-gerber-v13.py').read_text(encoding='utf8').split('for label,copper,mask,silk in')[0])
from shapely.affinity import rotate,translate
z.close();z=zipfile.ZipFile('PCB/eda/DTU-V0.14.4-60x75-Threefix-Gerber.zip');cache.clear()
cu=unary_union([g for g,d in geom('Gerber_TopLayer.GTL')[0] if d]);mask=unary_union([g for g,d in geom('Gerber_TopSolderMaskLayer.GTS')[0] if d])
world=lambda g:translate(rotate(g,180,origin=(0,0)),13.99999994,66.7)
no=world(box(-.95,-1.75,.95,.35));intrusion=cu.intersection(no.buffer(-.00001)).area
vs=[];fs=[];mat=None
for l in Path('PCB/references/dfm-models/b608ffd257624968b7f500f01fd0153b.obj').read_text(encoding='utf8').splitlines():
 p=l.split()
 if not p:continue
 if p[0]=='v':vs.append(tuple(map(float,p[1:4])))
 elif p[0]=='usemtl':mat=p[1]
 elif p[0]=='f':fs.append((mat,[int(x.split('/')[0])-1 for x in p[1:]]))
g=unary_union([Polygon([vs[i][:2] for i in f]) for m,f in fs if m=='3' and all(abs(vs[i][2])<.00001 for i in f)])
# Check only the metal in the manufacturer-permitted solder-land area.
allowed=g.intersection(box(-.5,1.0,.5,2));wg=world(translate(allowed,0,-.65));outside=wg.difference(cu).area
assert outside<1e-9 and wg.difference(mask).area<1e-9
assert intrusion<1e-8,intrusion
# Actual top-copper islands prove both side grounds still reach a grounded via.
plan=json.loads(Path('PCB/manifests/threefix-actual-routing-v14_4.json').read_text(encoding='utf8'))
islands=list(cu.geoms) if hasattr(cu,'geoms') else [cu];ground=[]
for x in [12.6,15.4]:
 pt=Point(x,67.35);island=next(gg for gg in islands if gg.distance(pt)<.002)
 hits=[v['id'] for v in plan['vias'] if v['net']=='GND' and island.distance(Point(v['x'],v['y']))<.002]
 assert hits,(x,'No connected ground via')
 ground.append({'pinCenterMm':[x,67.35],'connectedGroundVias':hits})
report={'reference':'Hirose U.FL legacy catalogue p3 recommended mounting pattern: signal 1.00 x 1.05 mm, inner edge 1.00 mm from connector centre; central area marked no conductive traces.','signalCopperLocalBoundsMm':[-.5,.35,.5,1.4],'signalPadShiftLocalYmm':.224887,'manufacturerNoTraceAreaTopCopperAreaMm2':intrusion,'factoryModelMetalInPermittedSolderAreaMm2':wg.area,'permittedMetalOutsideCopperMm2':outside,'permittedMetalOutsideMaskMm2':wg.difference(mask).area,'groundConnectivity':ground,'factoryDfmFullModelRatioMayRemainFlagged':True,'scope':'A geometric/reference review, not a full simulation of the factory DFM classifier or real reflow process.','U2AssemblyStillRequired':True,'U2PcbUnchanged':True}
Path('PCB/manifests/threefix-J5-manufacturer-review-v14_4.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('No-trace copper intrusion',intrusion,'permitted solder metal outside copper',outside,'both ground pads reach vias')
