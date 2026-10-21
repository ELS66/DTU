import json,collections
from pathlib import Path
P=Path('PCB')
def leaves(x):
 if isinstance(x,list):
  for z in x:yield from leaves(z)
 elif isinstance(x,dict):
  if 'list'in x:yield from leaves(x['list'])
  else:yield x
r=json.loads((P/'reports/pcb-drc-local-routing-v04.json').read_text(encoding='utf-8-sig'))['result'];ls=list(leaves(r));print(collections.Counter(x.get('errorType')for x in ls));print([x for x in ls if x.get('errorType')!='Connection Error'][:4])
plan=json.loads((P/'manifests/pcb-layout-plan-v04.json').read_text());print({r:plan['positions'][r]for r in ['U5','L2','L1','U4','D14','L3']})
