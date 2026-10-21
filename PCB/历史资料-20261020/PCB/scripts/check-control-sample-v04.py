from pathlib import Path
import json,collections
P=Path('PCB')
def leaves(x):
 if isinstance(x,list):
  for z in x:yield from leaves(z)
 elif isinstance(x,dict):
  if 'list'in x:yield from leaves(x['list'])
  else:yield x
ls=list(leaves(json.loads((P/'reports/pcb-drc-control-sample-v04.json').read_text(encoding='utf-8-sig'))['result']));print(collections.Counter(x.get('errorType')for x in ls));print('Q base remaining',[x.get('net')for x in ls if x.get('net')in ['Q1_BASE','Q2_BASE','Q3_BASE','Q4_BASE']]);print('nonconnection',[x for x in ls if x.get('errorType')!='Connection Error'][:3])
