import json
from pathlib import Path
cs=json.loads(Path('PCB/manifests/pcb-pads-power-v07.json').read_text(encoding='utf-8-sig'))['result']
for c in cs:
 if c['ref'] in ['D10','C50','C51','D18','D19','D20','D21','R60','R61','R15','R16','R92','R93','C109']:
  print(c['ref'],[(q.get('number'),q['net'],round(q['x']*.0254,3),round(q['y']*.0254,3)) for q in c['pads']])
s=json.loads(Path('PCB/manifests/slots-v07.json').read_text(encoding='utf-8-sig'))['result'];print('regions',str(s['regions'])[:600]);print('footprint',str(s['footprint'])[:800])
if s.get('footprint'):
 for l in s['footprint'].splitlines():
  if any(x in l for x in ['SLOT','REGION','e68']):print(l)
