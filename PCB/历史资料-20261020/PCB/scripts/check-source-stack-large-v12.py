import json,collections
from pathlib import Path
P=Path('PCB');src=json.load(open(P/'manifests/pcb-source-routing-resume-large-v12.json',encoding='utf-8'))['result']['source']
rows=[(json.loads(l.split('||')[0]),json.loads(l.split('||')[1].rstrip('|'))) for l in src.splitlines() if '||' in l]
print('recordCounts',collections.Counter(h['type'] for h,r in rows))
stack=[]
for h,r in rows:
 if h['type']=='LAYER_PHYS':stack.append({'id':h['id'],**r})
 if h['type']=='HOLE':print('hole',h,r)
print('stack',stack)
(P/'reports/叠层核对-V0.12.json').write_text(json.dumps(stack,ensure_ascii=False,indent=2),encoding='utf-8')
