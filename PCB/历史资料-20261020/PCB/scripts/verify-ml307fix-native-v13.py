"""Verify native source, PCB geometry and assembly data for corrected ML307R footprint."""
from pathlib import Path
import json,zipfile,math,collections,csv,io
R=Path('PCB');M=R/'manifests';E=R/'eda'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
code=(R/'scripts/package-silkclean-v13.py').read_text(encoding='utf8');exec(code[code.index('def rows('):code.index('before=rows(')]);exec(code[code.index('def active_project('):code.index('oldproj=active_project(')])
before=rows(load(M/'ml307fix-before-source-v13.json')['result']['source']);after=rows(load(M/'ml307fix-reopened-source-v13.json')['result']['source']);changes=load(M/'ml307fix-routing-diff-v13.json');applied=load(M/'ml307fix-applied-source-v13.json')['result'];expected=load(M/'ml307fix-rerouted-plan-v13.json')
changed=[k for k in before.keys()|after.keys() if before.get(k)!=after.get(k)];types=collections.Counter(k[0] for k in changed);print('PCB source changed',types)
assert all(k[0] in ['VIA','POLY','POURED','COMPONENT','ATTR'] for k in changed)
assert {k[1] for k in changed if k[0]=='COMPONENT'}=={c['id'] for c in load(M/'ml307fix-apply-parameters-v13.json')['moves']}
for k in changed:
 if k[0]=='COMPONENT':assert all(before[k].get(f)==after[k].get(f) for f in before[k].keys()|after[k].keys() if f not in ['positionX','positionY','x','y'])
 if k[0]=='ATTR':assert all(before[k].get(f)==after[k].get(f) for f in before[k].keys()|after[k].keys() if f not in ['x','y'])
assert load(M/'ml307fix-pcb-drc-v13.json')['result']==[]
plan={'routes':[],'vias':[]}
for (t,i),q in after.items():
 if t=='VIA':plan['vias'].append({'id':i,'net':q['netName'],'x':q['centerX']*.0254,'y':q['centerY']*.0254,'diameter':q['viaDiameter']*.0254,'hole':q['holeDiameter']*.0254})
 if t=='POLY' and q['layerId'] in [1,2,15,16] and q['netName']:
  vs=[v*.0254 for v in q['path'] if isinstance(v,(int,float))];plan['routes'].append({'id':i,'net':q['netName'],'layer':q['layerId'],'widthMm':q['width']*.0254,'pointsMm':list(map(list,zip(vs[::2],vs[1::2])))})
route_ids={f'ml307_new_{i}':v for i,v in enumerate(applied['createdRoutes'])};via_ids={f'ml307_via_{i}':v for i,v in enumerate(applied['createdVias'])}
for kind,ids in [('routes',route_ids),('vias',via_ids)]:
 actual={v['id']:v for v in plan[kind]};assert len(actual)==len(expected[kind])
 for q in expected[kind]:
  p=actual[ids.get(q['id'],q['id'])];assert p['net']==q['net']
  if kind=='routes':assert p['layer']==q['layer'] and abs(p['widthMm']-q['widthMm'])<.00001 and len(p['pointsMm'])==len(q['pointsMm']) and all(math.dist(a,b)<.00001 for a,b in zip(p['pointsMm'],q['pointsMm']))
  else:assert all(abs(p[f]-q[f])<.00001 for f in ['x','y','diameter','hole'])
save(M/'ml307fix-actual-routing-v13.json',plan)
# Compare all active project documents so electrical/schematic data cannot be silently changed by import.
a=active_project(E/'DTU-V0.13-60x70-Leadholefix.epro2');b=active_project(E/'DTU-V0.13-60x70-ML307fix.epro2');project_changes=[k for k in a.keys()|b.keys() if a.get(k)!=b.get(k)];normalization=[];fp='6b69a40d60760f97';fpc=collections.Counter()
for k in project_changes:
 old,new=a.get(k),b.get(k)
 if k[0]=='PCB':continue
 if k[0]=='CONFIG' and k[2]=='META' and isinstance(old,dict) and set(old)=={'defaultSheet'} and new is None:normalization.append(k);continue
 if k[0]=='FOOTPRINT' and k[2]=='ELE_PLACEHOLDER':normalization.append(k);continue
 if k[0]=='BLOB' and old=={} and new is None:normalization.append(k);continue
 assert k[0]=='FOOTPRINT' and k[1]==fp,(k,old,new)
 fpc[k[2]]+=1
assert fpc=={'PAD':109,'FILL':109,'ATTR':1,'META':1},fpc
pads_master=[(k,b[k]) for k in b if k[0]=='FOOTPRINT' and k[1]==fp and k[2]=='PAD'];assert len(pads_master)==109
outer=[]
for k,p in pads_master:
 d=p['defaultPad'];w,h=d['width']*.0254,d['height']*.0254
 if w>2.5:assert abs(w-2.6)<1e-10 and abs(h-.6)<1e-10 and d['radius']==100;outer.append(p)
 else:assert (round(w,3),round(h,3)) in [(1,.7),(1.3,1.3)]
assert len(outer)==48
refs=load(M/'u2-ml307-physical-reference-review-v13.json')['physicalPads'];oldmodel=load(M/'u2-pin-boundary-library-audit-v13.json')['rows'];models=[]
for r in oldmodel:
 q=b[('FOOTPRINT',fp,'FILL',r['modelId'])];vals=[v*.0254 for v in q['path'][0] if isinstance(v,(int,float))];xx,yy=vals[::2],vals[1::2];bounds=[min(xx),min(yy),max(xx),max(yy)];ref=next(z for z in refs if z['pin']==r['pin']);assert max(abs(x-y) for x,y in zip(bounds,ref['manufacturerNominalPhysicalBoundsMm']))<1e-10;models.append(bounds)
# Assembly set stable, placement coordinates must come from the new native export.
cpl=list(csv.DictReader(io.StringIO((E/'DTU-V0.13-ML307fix-CPL-native').read_text(encoding='utf16')),delimiter='\t'));native={q['Designator']:q for q in cpl};oldcpl=list(csv.DictReader((E/'DTU-V0.13-Leadholefix-CPL-99-Top.csv').open(encoding='utf-8-sig')));default={q['Designator'] for q in oldcpl};assert len(default)==99 and default<=native.keys()
newrows=[];changedplacements=[]
for q in oldcpl:
 n=native[q['Designator']];r={**q,'Mid X':n['Mid X'],'Mid Y':n['Mid Y'],'Layer':n['Layer'],'Rotation':n['Rotation']};newrows.append(r)
 assert n['Layer']=='T' and (float(q['Rotation'])-float(n['Rotation']))%360<.00001
 if any(abs(float(q[f].removesuffix('mm'))-float(n[f].removesuffix('mm')))>0.002 for f in ['Mid X','Mid Y']):changedplacements.append(q['Designator'])
assert set(changedplacements)=={'J5','R50','R60','R61'},changedplacements
with (E/'DTU-V0.13-ML307fix-CPL-99-Top.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=oldcpl[0].keys());w.writeheader();w.writerows(newrows)
bom=list(csv.DictReader((E/'DTU-V0.13-Leadholefix-BOM-99.csv').open(encoding='utf-8-sig')));u2=next(c for c in load(M/'ml307fix-final-pads-v13.json')['result'] if c['ref']=='U2');next(q for q in bom if q['Designator']=='U2')['Footprint']=u2['footprint']['name']
assert {q['Designator'] for q in bom}==default
with (E/'DTU-V0.13-ML307fix-BOM-99.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=bom[0].keys());w.writeheader();w.writerows(bom)
verification={'PCB_DRC':0,'factoryDfmPassed':False,'nativeCopperMatchesPlan':True,'schematicAndPinNetsUnchanged':True,'changedPCBSourceTypes':dict(types),'changedFootprintTypes':dict(fpc),'normalizedImportMetadataCount':len(normalization),'footprintMaster':fp,'footprintName':u2['footprint']['name'],'outerPadCount':48,'outerPadMm':[2.6,.6],'outerRadiusMm':.3,'innerPadCount':61,'physicalLeadModelsChecked':109,'modelExactlyMatchesReconstructedManufacturerNominalDimensions':True,'componentCount':104,'defaultAssemblyCount':99,'movedComponents':['J5','R50','R60','R61','C50','C51'],'movedPopulatedPlacements':changedplacements,'movedVias':len(changes['viaTargets']),'newVias':len(changes['newVias']),'viaCount':len(plan['vias']),'routeCount':len(plan['routes'])}
save(M/'ml307fix-native-verification-v13.json',verification);print(json.dumps(verification,ensure_ascii=True))

