import json
from pathlib import Path
p=Path('PCB');cs=json.loads((p/'manifests/pcb-pads-before-layout-v05.json').read_text(encoding='utf-8-sig'))['result'];plan=json.loads((p/'manifests/revision-v05.json').read_text(encoding='utf-8'));errors=[];n=0
for c in cs:
 r=c['ref']
 if r not in plan['expected']:errors.append('Unexpected '+r);continue
 for pad in c['pads']:
  expected=plan['expected'][r].get(pad['number'],'');n+=1
  if pad['net']!=expected:errors.append(f'{r}:{pad["number"]} {pad["net"]} expected {expected}')
report={'status':'PASS' if not errors else 'FAIL','components':len(cs),'physicalPads':n,'nettedPads':sum(bool(a['net']) for c in cs for a in c['pads']),'errors':errors}
(p/'reports/pcb-pad-validation-v05.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
