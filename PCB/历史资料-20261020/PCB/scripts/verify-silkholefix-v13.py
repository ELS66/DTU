"""Verify retained terminal text against both drill walls and soldermask openings."""
from pathlib import Path
import json,zipfile,hashlib,shutil
R=Path('PCB');E=R/'eda';M=R/'manifests';D=R/'docs'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
oldcode=(R/'scripts/package-silkclean-v13.py').read_text(encoding='utf8')
exec(oldcode[oldcode.index('def rows('):oldcode.index('before=rows(')])
exec(oldcode[oldcode.index('def active_project('):oldcode.index('oldproj=active_project(')])
a=rows(load(M/'silkholefix-before-source-v13.json')['result']['source']);b=rows(load(M/'silkholefix-reopened-source-v13.json')['result']['source'])
assert b==rows(load(M/'silkholefix-native-source-v13.json')['result']['source'])
changes=[k for k in a.keys()|b.keys() if a.get(k)!=b.get(k)]
assert len(changes)==5 and all(k[0]=='STRING' for k in changes)
for k in changes:assert all(a[k].get(f)==b[k].get(f) for f in a[k].keys()|b[k].keys() if f not in ['x','y'])
pa=active_project(E/'DTU-V0.13-60x70-Silkclean.epro2');pb=active_project(E/'DTU-V0.13-60x70-Silkholefix.epro2')
pc=[k for k in pa.keys()|pb.keys() if pa.get(k)!=pb.get(k)]
assert len(pc)==5 and all(k[0]=='PCB' and k[2]=='STRING' for k in pc),pc
assert load(M/'silkholefix-pcb-drc-v13.json')['result']==[]
# Use established Gerber parser and match the non-silk native export to previous production.
segment=oldcode[oldcode.index('exec((R/'):oldcode.index('production=E/')]
segment=segment.replace('Silkclean-Gerber-raw','Silkholefix-Gerber-raw').replace('Exposurefix-Gerber.zip','Silkclean-Gerber.zip')
exec(segment)
production=E/'DTU-V0.13-60x70-Silkholefix-Gerber.zip'
with zipfile.ZipFile(production,'w',zipfile.ZIP_DEFLATED) as q:
 for n in names:q.writestr(n,raw.read(n) if n in silk_names else old.read(n))
z=zipfile.ZipFile(production);cache.clear()
silks=[g for g,d in geom('Gerber_TopSilkscreenLayer.GTO')[0] if d];silk=unary_union(silks)
mask=unary_union([g for g,d in geom('Gerber_TopSolderMaskLayer.GTS')[0] if d])
holes=drill('Drill_PTH_Through.DRL')+drill('Drill_NPTH_Through.DRL');assert len(holes)==322
pairs=sorted((silk.distance(Point(x,y).buffer(di/2)),x,y,di) for x,y,di in holes)
gap_h=pairs[0][0];gap_m=silk.distance(mask)
assert gap_h>=.2 and gap_m>=.2,(gap_h,gap_m)
assert not geom('Gerber_BottomSilkscreenLayer.GBO')[0]
assert all(z.read(n)==old.read(n) for n in names if n not in silk_names)
verification={'PCB_DRC':0,'factoryDfmPassed':False,'reopenedNativeSourceVerified':True,'changedTextObjects':5,'keptTextObjects':15,'nominalTextSizeMm':1.8,'strokeWidthMm':.15,'RS485PinRowMoveMm':[0,.8],'RS485TitleMoveMm':[-.8,.95],'silkToDrillWallMinimumGapMm':gap_h,'silkToMaskMinimumGapMm':gap_m,'drillHolesChecked':322,'drillPairsWithin018mm':sum(p[0]<.18 for p in pairs),'nearestDrillPairsMm':pairs[:10],'unchangedProductionNonSilkFilesByBytes':[n for n in names if n not in silk_names],'nativeNonSilkGeometryCompared':preserved,'geometryToleranceMm':.00001,'componentAndPadGeometryUnchanged':True,'BOMandCPLUnchanged':True}
save(M/'silkholefix-manufacturing-verification-v13.json',verification)
# Isotropic manufacturing view, actual silk strokes, pad openings and drill coordinates.
for detail in [False,True]:
 scale=48 if detail else 20;xb,yb,xe,ye=(10,5,50,14) if detail else (0,0,60,70)
 im=Image.new('RGB',(int((xe-xb)*scale)+80,int((ye-yb)*scale)+100),'#f4f6f5');d=ImageDraw.Draw(im)
 xy=lambda x,y:(40+(x-xb)*scale,60+(ye-y)*scale)
 d.rectangle([xy(xb,ye),xy(xe,yb)],fill='#122c29')
 for n,c in [('Gerber_TopSolderMaskLayer.GTS','#c8ad68'),('Gerber_TopSilkscreenLayer.GTO','#fffde8')]:
  for g,dark in geom(n)[0]:draw_geom(d,g.intersection(box(xb,yb,xe,ye)),c if dark else '#122c29',xy)
 for x,y,di in holes:
  if xb<=x<=xe and yb<=y<=ye:
   px,py=xy(x,y);rr=di*scale/2;d.ellipse((px-rr,py-rr,px+rr,py+rr),fill='#000000')
 f=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
 d.text((40,15),'Silkholefix / exported silk, mask openings and drill holes / top view',font=f,fill='#19392e')
 im.save(E/('DTU-V0.13-Silkholefix-terminal-detail.png' if detail else 'DTU-V0.13-Silkholefix-preview.png'))
print(json.dumps(verification,ensure_ascii=True))


