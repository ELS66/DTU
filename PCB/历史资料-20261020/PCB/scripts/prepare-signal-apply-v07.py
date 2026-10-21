import json,math
from pathlib import Path
p=Path('PCB');d=json.loads((p/'manifests/signal-routing-plan-v07.json').read_text());keep=[];drop=[]
for v in d['vias']:
 near=next((q for q in keep if q['net']==v['net'] and math.dist((v['x'],v['y']),(q['x'],q['y']))<.35),None)
 if near:drop.append(v)
 else:keep.append(v)
d['vias']=keep;d['deduplicatedVias']=drop;(p/'manifests/signal-routing-plan-v07.json').write_text(json.dumps(d,indent=2))
head=(p/'scripts/plan-signals-v07.py').read_text();tail=head[head.index("guard='if("):];tail=tail.replace("newvias","keep").replace(" for r in new]"," for r in d['routes']]")
exec(tail)
print({'routes':len(d['routes']),'vias':len(keep),'removedCloseVias':len(drop),'failedConnections':len(d['failed']),'batches':math.ceil((len(keep)+len(d['routes']))/35)})
