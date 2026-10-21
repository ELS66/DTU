import json,collections
from pathlib import Path
p=Path('PCB');d=json.loads((p/'reports/pcb-drc-power-v07.json').read_text(encoding='utf-8-sig'))['result'];cnt=collections.Counter();out=[]
def walk(x):
 if isinstance(x,dict):
  if 'globalIndex' in x and 'errorType' in x:cnt[x['errorType']]+=1;out.append(x) if x['errorType']!='Connection Error' else None;return
  for v in x.values():walk(v)
 elif isinstance(x,list):
  for v in x:walk(v)
walk(d);print(dict(cnt));print([(x['errorObjType'],x.get('obj1'),x.get('obj2'),x.get('explanation',{}).get('param')) for x in out][:15]);(p/'reports/pcb-drc-summary-power-v07.json').write_text(json.dumps(dict(cnt),indent=2));(p/'reports/power-routing-clearance-errors-v07.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
