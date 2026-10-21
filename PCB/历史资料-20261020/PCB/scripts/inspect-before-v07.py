import json
from pathlib import Path
p=Path('PCB');start=json.loads((p/'manifests/start-v07.json').read_text(encoding='utf-8-sig'))['result'];print('jobs',[(x['key'],x['data'].get('status')) for x in start['jobs']]);print('pours',start['pours']);cs=json.loads((p/'manifests/pcb-pads-before-v07.json').read_text(encoding='utf-8-sig'))['result'];rs=['U4','U5','U11','L1','L2','L3','C80','C81','C90','C91','C92','C93','C94','C95','C96','C97','C98','C99','C106','C107','C108','C109','R90','R91','R92','R93','D14']
for c in cs:
 if c['ref'] in rs:print(c['ref'],[round(c[k]*.0254,2) for k in ['x','y']],c['rotation'],[(q['number'],q['net'],round(q['x']*.0254,2),round(q['y']*.0254,2)) for q in c['pads']])
