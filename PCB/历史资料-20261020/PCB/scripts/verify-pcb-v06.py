import json,collections
from pathlib import Path
p=Path('PCB');cs=json.loads((p/'manifests/pcb-after-layout-v06.json').read_text(encoding='utf-8-sig'))['result'];plan=json.loads((p/'manifests/revision-v06.json').read_text(encoding='utf-8'));errors=[]
if {c['ref'] for c in cs}!=set(plan['expected']):errors.append('Reference mismatch')
for c in cs:
 for q in c['pads']:
  ex=plan['expected'][c['ref']].get(q['number'],'')
  if q['net']!=ex:errors.append(f"{c['ref']}:{q['number']} expected {ex} actual {q['net']}")
 if not(0<c['x']*.0254<60 and 0<c['y']*.0254<70):errors.append('Outside '+c['ref'])
r={'status':'PASS' if not errors else 'FAIL','components':len(cs),'physicalPads':sum(len(c['pads']) for c in cs),'nettedPads':sum(bool(q['net']) for c in cs for q in c['pads']),'errors':errors};(p/'reports/pcb-pad-validation-v06.json').write_text(json.dumps(r,indent=2));print(r)
d=json.loads((p/'reports/pcb-drc-v06.json').read_text(encoding='utf-8-sig'))['result'];counts=collections.Counter()
def walk(x):
 if isinstance(x,dict):
  if 'globalIndex' in x and 'errorType' in x:counts[x['errorType']]+=1;return
  for v in x.values():walk(v)
 elif isinstance(x,list):
  for v in x:walk(v)
walk(d);print('DRC',dict(counts));(p/'reports/pcb-drc-summary-v06.json').write_text(json.dumps(dict(counts),indent=2))
r=json.loads((p/'manifests/pcb-image-v06.json').read_text(encoding='utf-8-sig'))['result'];(p/'reports/PCB-V0.6.png').write_bytes(bytes(r['bytes']))
