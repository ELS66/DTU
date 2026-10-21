import json
from pathlib import Path
x=json.loads(Path('PCB/reports/pcb-drc-v06.json').read_text(encoding='utf-8-sig'))['result']
def walk(x):
 if isinstance(x,dict):
  if x.get('errorType')=='Netlist Error' and 'globalIndex' in x:print(json.dumps(x,ensure_ascii=True));return
  for v in x.values():walk(v)
 elif isinstance(x,list):
  for v in x:walk(v)
walk(x)
