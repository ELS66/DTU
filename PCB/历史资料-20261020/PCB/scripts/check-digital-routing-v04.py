from pathlib import Path
import json,collections
P=Path('PCB')
def leaves(x):
 if isinstance(x,list):
  for z in x:yield from leaves(z)
 elif isinstance(x,dict):
  if 'list'in x:yield from leaves(x['list'])
  else:yield x
ls=list(leaves(json.loads((P/'reports/pcb-drc-digital-routing-v04.json').read_text(encoding='utf-8-sig'))['result']));print('DRC',collections.Counter(x.get('errorType')for x in ls));print('remainingnets',collections.Counter(x.get('net')for x in ls if x.get('errorType')=='Connection Error'));print('other',str([x for x in ls if x.get('errorType')!='Connection Error'])[:3000]);sel=json.loads((P/'manifests/pcb-digital-route-nets-v04.json').read_text());remaining=sorted(set(x.get('net')for x in ls if x.get('net')in sel));print('selected remaining',remaining)
