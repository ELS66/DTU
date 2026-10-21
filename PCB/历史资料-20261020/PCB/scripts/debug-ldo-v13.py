from pathlib import Path
exec(Path('PCB/scripts/router-v13.py').read_text(encoding='utf8'))
load_plan(P/'manifests/critical-routing-v13.json')
for ref,pin in [('C93','1'),('U5','6'),('C106','1')]:
 q=next(p for p in pads if p['ref']==ref and p['number']==pin);print(ref,'obst dist',q['geom'].distance(obstacles(q['net'],1)),'center',Point(q['x'],q['y']).distance(obstacles(q['net'],1)),flush=True);v=addvia(q['net'],(q['x'],q['y']),.6,.3,(q['x'],q['y']),1,.35);print('fanout',v,flush=True)
save_plan('debug-ldo-v13')
