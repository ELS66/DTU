import json,math
from pathlib import Path
cs=json.loads(Path('PCB/manifests/pcb-pads-before-v07.json').read_text(encoding='utf-8-sig'))['result'];by={c['ref']:c for c in cs}
for r,nums in [('U2',['42','43']),('U1',['2']),('J5',['2'])]:
 print(r,[(q['number'],q['x']*.0254,q['y']*.0254) for q in by[r]['pads'] if q['number'] in nums])
for r in ['U4','L1','C80','U5','L2','U11','L3','D14']:
 c=by[r];b=c['bbox'];print(r,'bodybox',{k:round(v*.0254,2) for k,v in b.items()})
