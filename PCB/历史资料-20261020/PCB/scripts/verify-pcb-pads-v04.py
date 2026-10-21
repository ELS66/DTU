import json,collections
from pathlib import Path
P=Path('PCB');n=json.loads((P/'reports/full-schematic-v04.net').read_text(encoding='utf-8'));cs=json.loads((P/'manifests/pcb-layout-pads-v04.json').read_text(encoding='utf-8-sig'))['result'];exp=json.loads((P/'manifests/full-schematic-netmap.json').read_text(encoding='utf-8'));by={c['ref']:c for c in cs};err=[]
for uid,c in n['components'].items():
 r=c['props']['Designator'];p=by[r]
 if p['uid']!=c['props']['Unique ID']:err.append([r,p['uid'],c['props']['Unique ID']])
 for pin,net in exp.get(r,{}).items():
  pads=[x for x in p['pads']if x['number']==pin]
  if not pads or any(x['net']!=net for x in pads):err.append([r,pin,net,pads])
rep={'status':'PASS'if not err else'FAIL','components':len(cs),'pads':sum(len(c['pads'])for c in cs),'pinNetAssertions':sum(len(x)for x in exp.values()),'nettedPads':sum(bool(p['net'])for c in cs for p in c['pads']),'errors':err}
(P/'reports/pcb-pad-validation-v04.json').write_text(json.dumps(rep,indent=2));print(rep)
d=json.loads((P/'reports/pcb-drc-layout-v04.json').read_text(encoding='utf-8-sig'))['result'];print('DRC',str(d)[:2500])
