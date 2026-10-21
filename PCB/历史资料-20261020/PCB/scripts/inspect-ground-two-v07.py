import json
from pathlib import Path
cs=json.loads(Path('PCB/manifests/pcb-pads-power-v07.json').read_text(encoding='utf-8-sig'))['result'];r=json.loads(Path('PCB/manifests/routing-fixed-signals-v07.json').read_text(encoding='utf-8-sig'))['result']
for c in cs:
 for p in c['pads']:
  if p.get('id')=='27e64738f6dde1f7e91' or c['ref']=='U1' and p.get('number') in ['33','34','35']:print(c['ref'],p)
for typ in ['lines','polys','vias']:
 for v in r[typ]:
  if v['id']=='6baf67fa4a6c4f0a':print(typ,v)
