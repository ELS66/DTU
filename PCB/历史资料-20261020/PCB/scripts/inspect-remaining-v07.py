import json,collections
from pathlib import Path
s=json.loads(Path('PCB/reports/pcb-source-v07.json').read_text(encoding='utf-8-sig'))['result']['source'];print(type(s),str(s)[:300])
if isinstance(s,str):
 out=[]
 for l in s.splitlines():
  if '||' in l:
   a,b=l.split('||',1);out.append((json.loads(a),json.loads(b.rstrip('|'))))
 Path('PCB/reports/pcb-records-v07.json').write_text(json.dumps(out))
 print(collections.Counter(h['type'] for h,v in out))
 for h,v in out:
  if 'REGION' in h['type'] or ('b5d49da068ac13f3' in str(h)):print(h,str(v)[:1600])
cs=json.loads(Path('PCB/manifests/pcb-pads-power-v07.json').read_text(encoding='utf-8-sig'))['result']
for c in cs:
 if c['ref'] in ['D10','C50','C51','D18','D19','D20','D21','R60','R61','R15','R16','R92','R93','C109']:
  print(c['ref'],[(q['num'],q['net'],round(q['x']*.0254,3),round(q['y']*.0254,3)) for q in c['pads']])
