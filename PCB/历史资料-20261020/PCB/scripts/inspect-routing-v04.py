import json,collections
from pathlib import Path
P=Path('PCB')
def leaves(x):
 if isinstance(x,list):
  for z in x:yield from leaves(z)
 elif isinstance(x,dict):
  if 'list'in x:yield from leaves(x['list'])
  else:yield x
for f in ['pcb-drc-association-v04.json']:
 r=json.loads((P/'reports'/f).read_text(encoding='utf-8-sig'))['result'];print(f,collections.Counter(x.get('errorType')for x in leaves(r)))
c=json.loads((P/'reports/pcb-rules-v04.json').read_text(encoding='utf-8-sig'))['result']['rules']['config'];print('categories',list(c));print('Routing',c.get('Routing'));print('Other',c.get('Other'))
cs=json.loads((P/'manifests/pcb-layout-pads-v04.json').read_text(encoding='utf-8-sig'))['result']
for r in ['U4','U5','U11','L1','L2','L3','D14','C90','C91','C92','C93','C94','C95','C96','C97','C98','C99','C106','C107','C108','C109','R90','R91','R92','R93','J5','R50','D10']:
 z=next(c for c in cs if c['ref']==r);print(r,[(p['number'],p['net'],round(p['x']*.0254,3),round(p['y']*.0254,3))for p in z['pads']])
