import json,collections,math,zipfile
from pathlib import Path
P=Path('PCB');expected=json.loads((P/'manifests/routing-optimized-v13.json').read_text())
def rows(path):
 s=json.loads(path.read_text(encoding='utf8'))['result']['source'];out=[]
 for l in s.splitlines():
  if '||' not in l:continue
  h,z=l.split('||',1);out.append((json.loads(h),json.loads(z.removesuffix('|'))))
 return out
before=rows(P/'manifests/source-before-routing-opt-v13.json');after=rows(P/'manifests/source-after-routing-opt-v13.json')
unchanged=['COMPONENT','PAD_NET','PAD','PRIMITIVE','STRING','RULE','RULE_SELECTOR','REGION','POUR','LAYER_PHYS']
for t in unchanged:
 assert {h['id']:z for h,z in before if h['type']==t}=={h['id']:z for h,z in after if h['type']==t},'Unexpected change '+t
def extract(rows):
 plan={'routes':[],'vias':[]}
 for h,z in rows:
  if h['type']=='VIA':plan['vias'].append({'id':h['id'],'net':z['netName'],'x':z['centerX']*.0254,'y':z['centerY']*.0254,'diameter':z['viaDiameter']*.0254,'hole':z['holeDiameter']*.0254})
  if h['type']=='POLY' and z['layerId'] in [1,2,15,16] and z['netName']:
   assert all(not isinstance(q,str) or q=='L' for q in z['path'])
   vals=[v*.0254 for v in z['path'] if isinstance(v,(int,float))]
   plan['routes'].append({'id':h['id'],'net':z['netName'],'layer':z['layerId'],'widthMm':z['width']*.0254,'pointsMm':list(map(list,zip(vals[::2],vals[1::2])))})
 return plan
b=extract(before);a=extract(after)
def rsig(r):return(r['net'],r['layer'],round(r['widthMm'],4),tuple(round(v,4) for q in r['pointsMm'] for v in q))
assert collections.Counter(rsig(r) for r in a['routes'])==collections.Counter(rsig(r) for r in expected['routes'])
def vsig(v):return (v['net'],round(v['x'],4),round(v['y'],4))
assert collections.Counter(vsig(v) for v in a['vias'])==collections.Counter(vsig(v) for v in expected['vias'])
for v in a['vias']:
 q=next(q for q in expected['vias'] if vsig(q)==vsig(v))
 # Native primitive getters quantize diameter/hole to 0.1 mil; document source is authoritative.
 assert abs(v['diameter']-q['diameter'])<.003 and abs(v['hole']-q['hole'])<.003
protected={'GND','VDD_3V3','VDD_4G','VIN_IN','VIN_DIODE','VIN_PROT','SIM_VDD','LTE_VDD_EXT','LTE_SW','LTE_BST','LTE_FB','MCU_LDO_FB','LTE_ANT','LTE_RF_FEED','232_VMINUS'}
for kind in ['routes','vias']:
 filt=lambda p:sorted([r for r in p[kind] if r['net'] in protected or 'USB' in r['net'] or r['net'].startswith('232_C')],key=lambda r:r['id'])
 assert filt(a)==filt(b),'Protected copper changed '+kind
length=lambda p:sum(sum(math.dist(x,y) for x,y in zip(r['pointsMm'],r['pointsMm'][1:])) for r in p['routes'])
result={'unchangedSourceTypes':unchanged,'nativeCopperMatchesCandidate':True,'protectedCopperUnchanged':True,'oldTraceLengthMm':length(b),'newTraceLengthMm':length(a),'oldRoutes':len(b['routes']),'newRoutes':len(a['routes']),'oldVias':len(b['vias']),'newVias':len(a['vias']),'nativeViaHoleSizes':dict(collections.Counter(round(v['hole'],3) for v in a['vias']))}
(P/'manifests/routing-opt-source-verification-v13.json').write_text(json.dumps(result,indent=2))
(P/'manifests/routing-opt-baseline-source-v13.json').write_text(json.dumps(b,indent=2))
(P/'manifests/routing-optimized-source-v13.json').write_text(json.dumps(a,indent=2))
print(json.dumps(result,indent=2))
z=zipfile.ZipFile(P/'eda/DTU-V0.13-60x70-routing-optimized-raw');print(z.namelist())

