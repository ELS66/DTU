import json,math,collections
from pathlib import Path
P=Path('PCB');a=json.load(open(P/'manifests/pcb-pads-enlarged-v12.json'))['result'];b=json.load(open(P/'manifests/pcb-pads-reimported-final-v12.json'))['result'];by={z['ref']:z for z in a}
for c in b:
 o=by[c['ref']];dx=abs(c['x']-o['x'])*.0254;dy=abs(c['y']-o['y'])*.0254;rot=(c['rotation']-o['rotation']+180)%360-180
 if dx>.00001 or dy>.00001 or c['rotation']!=o['rotation'] or c['layer']!=o['layer']:print(c['ref'],'deltaMm',dx,dy,'angles',o['rotation'],c['rotation'],'norm',rot,'layers',o['layer'],c['layer'])
for name in ['pcb-source-routing-resume-large-v12.json','pcb-source-ground-final-large-v12.json','pcb-source-reimported-final-v12.json']:
 src=json.load(open(P/'manifests'/name))['result']['source'];phys=[];layers=[]
 for l in src.splitlines():
  if '||' not in l:continue
  h,j=l.split('||',1);h=json.loads(h);j=json.loads(j.rstrip('|')) if j.rstrip('|') else {}
  if h['type']=='LAYER_PHYS':phys.append((json.loads(h['id'])[1],j.get('thickness',0)*.0254,j['zIndex']))
  if h['type']=='LAYER' and j.get('layerId',0)>350:layers.append(j)
 print(name,phys,'TOTAL',sum(p[1] for p in phys));print('Dielectric layers',layers)
