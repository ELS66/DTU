import json,collections
from pathlib import Path
r=json.loads(Path('PCB/reports/pcb-drc-post-signals-v07.json').read_text(encoding='utf-8-sig'))['result'];f=[]
def flat(v):
 if isinstance(v,dict):
  if 'visible' in v and 'globalIndex' in v:f.append(v);return
  for x in v.values():flat(x)
 elif isinstance(v,list):
  for x in v:flat(x)
flat(r);print(collections.Counter(x['errorType'] for x in f));print('GND errors',sum(x.get('net')=='GND' for x in f));print('other disconnected nets',collections.Counter(x.get('net') for x in f if x['errorType']=='Connection Error' and x.get('net')!='GND'))
for x in f:
 if x['errorType']!='Connection Error':print({k:x.get(k) for k in ['errorType','errorObjType','objs','pos']})
d=json.loads(Path('PCB/manifests/routing-post-signals-v07.json').read_text(encoding='utf-8-sig'))['result']
for typ in ['lines','polys','vias']:
 for v in d[typ]:
  if v['id'] in ['f320888aa19ba9fd','ca8f3edb933a374f','4c98ceeab31765c8','9779ec451fa2c25f','8854b2976194731d']:print(typ,v)
