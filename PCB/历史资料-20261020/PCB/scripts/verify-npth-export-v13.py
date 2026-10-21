from pathlib import Path
import json,zipfile,re,math,collections
P=Path('PCB');E=P/'eda';M=P/'manifests'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
assert load(M/'npth-fixed-pcb-drc-v13.json')['result']==[]
def sourceRows(file):
 out={}
 for l in load(M/file)['result']['source'].splitlines():
  if '||' in l:
   h,b=l.split('||',1);h=json.loads(h)
   if h['type']!='DOCHEAD':out[(h['type'],h.get('id',''))]=json.loads(b.removesuffix('|'))
 return out
before=sourceRows('source-before-npth-fix-v13.json');after=sourceRows('npth-four-pad-fix-v13.json')
changed=[k for k in before.keys()|after.keys() if before.get(k)!=after.get(k)]
assert len(changed)==4 and all(k[0]=='PAD' for k in changed)
for k in changed:
 a,b=before[k],after[k]
 assert all(a.get(key)==b.get(key) for key in a.keys()|b.keys() if key not in ['defaultPad','topSolderExpansion','bottomSolderExpansion'])
 assert b['plated']==False and b['hole']['holeType']=='ROUND' and b['defaultPad']['width']==b['defaultPad']['height']<=.04
exec((P/'scripts/render-hy20-gerber-v13.py').read_text(encoding='utf8').split('for label,copper,mask,silk in')[0].replace('HY20','NPTHfix'))
npth=drill('Drill_NPTH_Through.DRL');pth=drill('Drill_PTH_Through.DRL');mounts=[p for p in npth if p[2]>3]
assert len(npth)==6 and len(pth)==316 and len(mounts)==4
assert all(any(math.dist((x,y),v[:2])<.001 for v in mounts) for x,y in [(4,4),(56,4),(4,66),(56,66)])
layers=['Gerber_TopLayer.GTL','Gerber_BottomLayer.GBL','Gerber_InnerLayer1.G1','Gerber_InnerLayer2.G2']
removed={};replacements={}
for name in layers:
 text=z.read(name).decode('ascii');aps={};ap=None;out=[];points=[];dark=True
 for l in text.splitlines():
  m=re.match(r'%ADD(\d+)C,([.\d]+)\*%',l)
  if m:aps[int(m[1])]=float(m[2])
  m=re.match(r'G54D(\d+)\*',l)
  if m:ap=int(m[1])
  if l.startswith('%LPC'):dark=False
  if l.startswith('%LPD'):dark=True
  m=re.fullmatch(r'G01X(-?\d+)Y(-?\d+)D03\*',l)
  if m and dark and ap in aps and aps[ap]<=.0011:
   xy=(int(m[1])/1e6,int(m[2])/1e6)
   if any(math.dist(xy,p[:2])<.002 for p in mounts):
    points.append({'x':xy[0],'y':xy[1],'diameter':aps[ap]});continue
  out.append(l)
 assert len(points)==4,(name,points)
 replacements[name]=('\n'.join(out)+'\n').encode('ascii');removed[name]=points
files=layers+['Gerber_TopSilkscreenLayer.GTO','Gerber_BottomSilkscreenLayer.GBO','Gerber_TopSolderMaskLayer.GTS','Gerber_BottomSolderMaskLayer.GBS','Gerber_TopPasteMaskLayer.GTP','Gerber_BoardOutlineLayer.GKO','Drill_PTH_Through.DRL','Drill_NPTH_Through.DRL']
target=E/'DTU-V0.13-60x70-NPTHfix-Gerber.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as o:
 for name in files:o.writestr(name,replacements.get(name,z.read(name)))
with zipfile.ZipFile(target) as test:assert test.testzip() is None and len(test.namelist())==12
# Measure copper near each hole using ordered Gerber polarity; clip locally for efficiency.
z.close();z=zipfile.ZipFile(target);cache.clear();copper=[]
for name in layers:
 gg=geom(name)[0]
 for x,y,hole in mounts:
  clip=box(x-2.5,y-2.5,x+2.5,y+2.5);g=Polygon()
  for feature,dark in gg:
   q=feature.intersection(clip)
   if not q.is_empty:g=g.union(q) if dark else g.difference(q)
  # Drill area is removed physically. Outside it, no residual annular pad is allowed.
  outside=g.difference(Point(x,y).buffer(hole/2+.001))
  gap=outside.distance(Point(x,y))-hole/2 if not outside.is_empty else 2.5-hole/2
  copper.append({'layer':name,'x':x,'y':y,'copperClearanceFromHoleEdgeMm':gap,'copperAreaWithinHolePlus0_15mm':outside.intersection(Point(x,y).buffer(hole/2+.15)).area})
  assert gap>.15,(name,x,y,gap)
for name in ['Gerber_TopSolderMaskLayer.GTS','Gerber_BottomSolderMaskLayer.GBS']:
 mask=unary_union([g for g,d in geom(name)[0] if d])
 for x,y,hole in mounts:assert mask.buffer(.002).covers(Point(x,y).buffer(1.699)),(name,x,y)
result={'changedPrimitiveCount':4,'electricalCopperPrimitivesUnchanged':True,'componentPlacementsUnchanged':True,'NPTH':len(npth),'PTH':len(pth),'totalDrillHoles':len(npth)+len(pth),'mounts':mounts,'mountDiameterNominalMm':3.2,'maskOpeningNominalMm':3.4,'removedExporterZeroPadPlaceholderFlashes':removed,'copperAroundMounts':copper,'pcbDrcIssues':0,'factoryDfmRerun':'Pending','warningThresholdsUnchanged':True}
(M/'npth-export-verification-v13.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'changedPrimitives':4,'holes':len(npth)+len(pth),'removedFlashes':sum(len(p) for p in removed.values()),'minMountCopperGapMm':min(p['copperClearanceFromHoleEdgeMm'] for p in copper),'gerber':str(target)},ensure_ascii=True))
