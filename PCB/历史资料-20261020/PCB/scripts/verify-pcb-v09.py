import json,collections
from pathlib import Path
p=Path('PCB');cs=json.loads((p/'manifests/pcb-pads-final-v09.json').read_text(encoding='utf-8-sig'))['result'];plan=json.loads((p/'manifests/revision-v06.json').read_text(encoding='utf-8'));errors=[]
if {c['ref'] for c in cs}!=set(plan['expected']):errors.append('Reference mismatch')
for c in cs:
 for q in c['pads']:
  ex=plan['expected'][c['ref']].get(q['number'],'')
  if q['net']!=ex:errors.append(f"{c['ref']}:{q['number']} expected {ex} actual {q['net']}")
 if not(0<c['x']*.0254<60 and 0<c['y']*.0254<70):errors.append('Outside '+c['ref'])
r={'status':'PASS' if not errors else 'FAIL','components':len(cs),'physicalPads':sum(len(c['pads']) for c in cs),'nettedPads':sum(bool(q['net']) for c in cs for q in c['pads']),'errors':errors};(p/'reports/pcb-pad-validation-v09.json').write_text(json.dumps(r,indent=2));print(r)
