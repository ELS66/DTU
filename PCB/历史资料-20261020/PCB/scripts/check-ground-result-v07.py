import json,collections
from pathlib import Path
r=json.loads(Path('PCB/reports/pcb-drc-ground-v07.json').read_text(encoding='utf-8-sig'))['result'];f=[]
def rec(v):
 if isinstance(v,dict):
  if 'visible' in v and 'globalIndex' in v:f.append(v);return
  for x in v.values():rec(x)
 elif isinstance(v,list):
  for x in v:rec(x)
rec(r);print(collections.Counter(x['errorType'] for x in f));print('GND',sum(x.get('net')=='GND' for x in f));
for x in f:
 if x['errorType']!='Connection Error' or x.get('net')=='GND':print({k:x.get(k) for k in ['net','errorType','errorObjType','objs','pos']})
