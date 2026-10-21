from pathlib import Path
import json,zipfile,math,collections,csv,io
R=Path('PCB');M=R/'manifests';E=R/'eda'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2),encoding='utf8')
s=(R/'scripts/package-silkclean-v13.py').read_text(encoding='utf8');exec(s[s.index('def rows('):s.index('before=rows(')]);exec(s[s.index('def active_project('):s.index('oldproj=active_project(')])
before=rows(load(M/'ml307fix-reopened-source-v13.json')['result']['source']);after=rows(load(M/'clearancefix-final-source-v14.json')['result']['source']);cs=load(M/'clearancefix-final-pads-v14.json')['result'];ids=load(M/'clearancefix-native-id-map-v14.json');expected=load(M/'clearancefix-rerouted-plan-v14.json')
zero_routes=[r for r in expected['routes'] if sum(math.dist(x,y) for x,y in zip(r['pointsMm'],r['pointsMm'][1:]))<1e-7]
assert all(r['net']=='LTE_USB_DM_EXT' for r in zero_routes) and len(zero_routes)==1
expected['routes']=[r for r in expected['routes'] if r not in zero_routes]
assert len(cs)==104 and all(c['layer']==1 for c in cs)
assert load(M/'clearancefix-reopened-drc-v14.json')['result']==[]
for typ in ['PAD_NET','STRING','RULE','RULE_SELECTOR','LAYER_PHYS']:
 assert {k:v for k,v in before.items() if k[0]==typ}=={k:v for k,v in after.items() if k[0]==typ},typ
assert len([k for k in after if k[0]=='STRING'])==15
planned_moves={r['ref']:r['deltaMm'] for r in load(M/'clearancefix-stage-v14.json')['componentMoves']};planned_moves.update({r:(0,2) for r in ['D30','D31','D32','D33','D34','D35']})
for c in cs:
 old=before[('COMPONENT',c['id'])];new=after[('COMPONENT',c['id'])];delta=planned_moves.get(c['ref'],(0,0))
 assert all(old.get(k)==new.get(k) for k in old.keys()|new.keys() if k not in ['x','y'])
 assert abs((new['x']-old['x'])*.0254-delta[0])<1e-5 and abs((new['y']-old['y'])*.0254-delta[1])<1e-5
plan={'routes':[],'vias':[]}
for (t,i),q in after.items():
 if t=='VIA':plan['vias'].append({'id':i,'net':q['netName'],'x':q['centerX']*.0254,'y':q['centerY']*.0254,'diameter':q['viaDiameter']*.0254,'hole':q['holeDiameter']*.0254})
 if t=='POLY' and q['layerId'] in [1,2,15,16] and q['netName']:
  vals=[v*.0254 for v in q['path'] if isinstance(v,(int,float))];plan['routes'].append({'id':i,'net':q['netName'],'layer':q['layerId'],'widthMm':q['width']*.0254,'pointsMm':list(map(list,zip(vals[::2],vals[1::2])))})
for kind in ['routes','vias']:
 actual={q['id']:q for q in plan[kind]};assert len(actual)==len(expected[kind]),(kind,len(actual),len(expected[kind]))
 for r in expected[kind]:
  q=actual[ids[kind][r['id']]];assert q['net']==r['net']
  if kind=='routes':assert q['layer']==r['layer'] and abs(q['widthMm']-r['widthMm'])<1e-5 and len(q['pointsMm'])==len(r['pointsMm']) and all(math.dist(x,y)<1e-5 for x,y in zip(q['pointsMm'],r['pointsMm'])),r['id']
  else:assert all(abs(q[f]-r[f])<1e-5 for f in ['x','y','diameter','hole']),r['id']
save(M/'clearancefix-actual-routing-v14.json',plan)
a=active_project(E/'DTU-V0.13-60x70-ML307fix.epro2');b=active_project(E/'DTU-V0.14-60x75-Clearancefix.epro2');fp='6b69a40d60760f97';extra=[]
for k in a.keys()|b.keys():
 if a.get(k)==b.get(k):continue
 if k[0]=='PCB':continue
 if k[:3]==('BOARD','e7a0217c7788eb0d','META'):
  assert all(a[k].get(f)==b[k].get(f) for f in a[k].keys()|b[k].keys() if f!='title');continue
 if k[0]=='FOOTPRINT' and k[1]==fp:
  if k[2]=='FILL':assert a.get(k) is None and b[k]['layerId']==7,k
  else:assert k[2] in ['PAD','ATTR','META'],k
  continue
 if k[0]=='FOOTPRINT' and k[2]=='ELE_PLACEHOLDER':extra.append(k);continue
 if k[0]=='CONFIG' and k[2]=='META' and set(a.get(k,{}) or {})=={'defaultSheet'} and b.get(k) is None:extra.append(k);continue
 if k[0]=='BLOB' and a.get(k)=={} and b.get(k) is None:extra.append(k);continue
 if k[0]=='PANEL' and k[2]=='META' and b.get(k) is None:
  assert {v[2] for v in a if v[:2]==k[:2]}=={'CANVAS','META'} and a[k]['title']=='Panel1'
  extra.append(k);continue
 raise AssertionError(('Unexpected non-PCB change',k))
assert all(a[k]==b[k] for k in a if k[0]=='FOOTPRINT' and k[1]==fp and isinstance(a[k],dict) and a[k].get('layerId') in [48,50,51,52])
assert len([k for k in b if k[:3]==('FOOTPRINT',fp,'PAD')])==109
assert len([k for k in b if k[:3]==('FOOTPRINT',fp,'FILL') and b[k].get('layerId')==7])==48
for k,p in b.items():
 if k[:3]==('FOOTPRINT',fp,'PAD'):
  assert p['topPasteExpansion']==p['bottomPasteExpansion'] and p['topPasteExpansion']<0
oldcpl=list(csv.DictReader((E/'DTU-V0.13-ML307fix-CPL-99-Top.csv').open(encoding='utf-8-sig')));native={q['Designator']:q for q in csv.DictReader(io.StringIO((E/'DTU-V0.14-Clearancefix-CPL-native').read_text(encoding='utf16')),delimiter='\t')};default={r['Designator'] for r in oldcpl};assert len(default)==99
newcpl=[]
for q in oldcpl:
 n=native[q['Designator']];assert n['Layer']=='T' and (float(q['Rotation'])-float(n['Rotation']))%360<1e-5
 newcpl.append({**q,'Mid X':n['Mid X'],'Mid Y':n['Mid Y'],'Layer':n['Layer'],'Rotation':n['Rotation']})
with (E/'DTU-V0.14-Clearancefix-CPL-99-Top.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=oldcpl[0].keys());w.writeheader();w.writerows(newcpl)
bom=list(csv.DictReader((E/'DTU-V0.13-ML307fix-BOM-99.csv').open(encoding='utf-8-sig')));next(q for q in bom if q['Designator']=='U2')['Footprint']=next(c for c in cs if c['ref']=='U2')['footprint']['name']
assert {q['Designator'] for q in bom}==default
with (E/'DTU-V0.14-Clearancefix-BOM-99.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=bom[0].keys());w.writeheader();w.writerows(bom)
groups=list(csv.DictReader(io.StringIO((E/'DTU-V0.14-Clearancefix-BOM-native.csv').read_text(encoding='utf16')),delimiter='\t'));native_bom={v.strip() for row in groups for v in row['Designator'].split(',')};assert default<=native_bom
bodies=load(M/'clearancefix-body-margins-v14.json')['bodyBounds']
for ref in ['D30','D31','D32','D33','D34','D35']:bodies[ref]=[v+(2 if i%2 else 0) for i,v in enumerate(bodies[ref])]
u=bodies['U2'];gaps=[];bodybad=[]
for ref,p in bodies.items():
 if ref!='U2':gaps.append({'ref':ref,'gapMm':math.hypot(max(u[0]-p[2],p[0]-u[2],0),max(u[1]-p[3],p[1]-u[3],0))})
for i,(ref,p) in enumerate(bodies.items()):
 if ref not in default:continue
 for ref2,q in list(bodies.items())[:i]:
  if ref2 not in default:continue
  gap=math.hypot(max(p[0]-q[2],q[0]-p[2],0),max(p[1]-q[3],q[1]-p[3],0))
  if gap<.3:bodybad.append([ref,ref2,gap])
assert not bodybad and min(g['gapMm'] for g in gaps)>=3
save(M/'clearancefix-final-body-audit-v14.json',{'scope':'Unchanged library layer48 body geometry translated by actual component movements; not a replacement for vendor maximum-body tolerances or factory 3D checking.','bounds':bodies,'moduleNeighbors':sorted(gaps,key=lambda g:g['gapMm']),'defaultBodyGapsBelow0_3mm':bodybad})
usb={n:sum(sum(math.dist(x,y) for x,y in zip(r['pointsMm'],r['pointsMm'][1:])) for r in plan['routes'] if r['net']==n) for n in ['LTE_USB_DP','LTE_USB_DM','LTE_USB_DP_EXT','LTE_USB_DM_EXT']}
report={'boardMm':[60,75],'components':104,'defaultAssembly':99,'defaultDnp':['C50','C51','R32','J6','J7'],'copperLayers':4,'assemblySide':'Top','nativeReopenedDrcIssues':0,'routes':len(plan['routes']),'vias':len(plan['vias']),'schematicAndPinNetBindingsUnchanged':True,'physicalModelsUnchanged':True,'nativeCopperExactlyMatchesPlan':True,'movedComponents':planned_moves,'U2MinimumNominalBodyGapMm':min(g['gapMm'] for g in gaps),'defaultBodyGapsBelow0_3mm':0,'USBGeometricSegmentLengthSumsMm':usb,'factoryDfmPassed':False,'normalizationRecords':extra,'nativeRemovedCoincidentEndpointRoutes':zero_routes}
save(M/'clearancefix-native-verification-v14.json',report);print(json.dumps(report,ensure_ascii=True))
