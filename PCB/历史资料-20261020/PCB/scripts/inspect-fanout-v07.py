import json,collections
from pathlib import Path
p=Path('PCB');d=json.loads((p/'reports/pcb-drc-fanout-v07.json').read_text(encoding='utf-8-sig'))['result'];cnt=collections.Counter();e=[]
def walk(x):
 if isinstance(x,dict):
  if 'globalIndex' in x and 'errorType' in x:cnt[x['errorType']]+=1;e.append(x) if x['errorType']!='Connection Error' else None;return
  for v in x.values():walk(v)
 elif isinstance(x,list):
  for v in x:walk(v)
walk(d);print(dict(cnt));print(json.dumps(e,ensure_ascii=True)[:2000]);cs=json.loads((p/'manifests/pcb-pads-power-v07.json').read_text(encoding='utf-8-sig'))['result'];by={c['ref']:c for c in cs}
for r,nums in [('U2',['35','59','60']),('U1',['13','14']),('R15',['1','2']),('R16',['1','2']),('R60',['1','2']),('R61',['1','2']),('J6',['2','3']),('J7',['2','3']),('R50',['1','2']),('D10',['1','2'])]:print(r,[(q['number'],q['net'],round(q['x']*.0254,3),round(q['y']*.0254,3)) for q in by[r]['pads'] if q['number'] in nums])
