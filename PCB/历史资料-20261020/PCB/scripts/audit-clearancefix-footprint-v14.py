"""Read exported copper/stencil, then measure true nominal lead containment."""
from pathlib import Path
import json,zipfile,math
R=Path('PCB');M=R/'manifests';E=R/'eda'
exec((R/'scripts/render-hy20-gerber-v13.py').read_text(encoding='utf8').split('for label,copper,mask,silk in')[0])
from shapely.affinity import rotate,translate
from shapely.strtree import STRtree
z.close();z=zipfile.ZipFile(E/'DTU-V0.14-60x75-Clearancefix-Gerber-raw');cache.clear()
s=(R/'scripts/package-silkclean-v13.py').read_text(encoding='utf8');exec(s[s.index('def active_project('):s.index('oldproj=active_project(')])
a=active_project(E/'DTU-V0.14-60x75-Clearancefix.epro2');fp='6b69a40d60760f97';pcb='4211128ecf040c100b33238447713203';c=a[('PCB',pcb,'COMPONENT','9a20c59b6357d964')]
refs=json.loads((M/'u2-ml307-physical-reference-review-v13.json').read_text(encoding='utf8'))['physicalPads']
features={n:[g for g,d in geom(n)[0] if d] for n in ['Gerber_TopLayer.GTL','Gerber_TopPasteMaskLayer.GTP','Gerber_TopSolderMaskLayer.GTS']}
trees={n:STRtree(gs) for n,gs in features.items()};out=[]
def world(g):return translate(rotate(g,c['angle'],origin=(0,0)),c['x']*.0254,c['y']*.0254)
for k,p in a.items():
 if k[:3]!=('FOOTPRINT',fp,'PAD'):continue
 ref=next(r for r in refs if r['pin']==p['num']);metal=world(box(*ref['manufacturerNominalPhysicalBoundsMm']));outer=p['defaultPad']['width']*.0254>2.5
 w,h=(2.6,.6) if outer else (p['defaultPad']['width']*.0254-.1,p['defaultPad']['height']*.0254-.1)
 paste=LineString([(-1,0),(1,0)]).buffer(.3,quad_segs=128) if outer else box(-w/2,-h/2,w/2,h/2)
 paste=world(translate(rotate(paste,p['padAngle'],origin=(0,0)),p['centerX']*.0254,p['centerY']*.0254))
 dw,dh=p['defaultPad']['width']*.0254,p['defaultPad']['height']*.0254
 radius=.05 if outer else 0
 copper=box(-dw/2+radius,-dh/2+radius,dw/2-radius,dh/2-radius).buffer(radius) if radius else box(-dw/2,-dh/2,dw/2,dh/2)
 copper=world(translate(rotate(copper,p['padAngle'],origin=(0,0)),p['centerX']*.0254,p['centerY']*.0254))
 center=paste.centroid
 matches={}
 for n,gs in features.items():
  inds=[int(i) for i in trees[n].query(center.buffer(.002))]
  expected=paste if 'Paste' in n else copper.buffer(.0508) if 'Solder' in n else copper
  assert inds,(p['num'],n)
  dist,i=min((gs[i].hausdorff_distance(expected),i) for i in inds);g=gs[i]
  if 'Paste' in n:assert dist<.00002,(p['num'],n,dist)
  else:assert g.covers(metal),(p['num'],n,metal.difference(g).area)
  matches[n]={'hausdorffToExpectedMm':dist,'nominalMetalToEdgeMm':g.boundary.distance(metal),'areaMm2':g.area}
 out.append({'pin':p['num'],'outer':outer,'checks':matches})
assert len(out)==109
report={'scope':'All 109 nominal physical lead rectangles versus actual native Gerber pad copper and solder mask; actual stencil compared separately to original nominal land shapes. This is not a factory DFM result or tolerance-stack certification.','physicalModelsUnchanged':True,'copperContainsNominalLeadCount':109,'pasteAperturesMatchOriginalNominalCount':109,'minimumNominalLeadCopperMarginMm':min(q['checks']['Gerber_TopLayer.GTL']['nominalMetalToEdgeMm'] for q in out),'rows':out}
(M/'clearancefix-footprint-audit-v14.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='rows'},ensure_ascii=True))
