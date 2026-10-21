import json
from pathlib import Path
p=Path('PCB');w=json.loads((p/'manifests/pcb-netlist-v06.json').read_text(encoding='utf-8-sig'))['result']['netlist'];print(type(w).__name__);print(str(w)[:250])
if isinstance(w,str):w=json.loads(w)
(p/'reports/pcb-netlist-v06.net').write_text(json.dumps(w,ensure_ascii=False,indent=2),encoding='utf-8')
s=json.loads((p/'reports/full-schematic-v06.net').read_text(encoding='utf-8'));a={x['props']['Designator']:x for x in s['components'].values()};b={x['props']['Designator']:x for x in w['components'].values()};print('references',set(a)^set(b))
for r in a:
 if r not in b:continue
 dif={k:[v,b[r]['props'].get(k)] for k,v in a[r]['props'].items() if b[r]['props'].get(k)!=v}
 if dif:print(r,json.dumps(dif,ensure_ascii=True))
