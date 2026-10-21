import json,math
from pathlib import Path
P=Path('PCB');native=json.load(open(P/'manifests/routing-pass2-large-v12.json'))['result'];by={v['id']:v for v in native['vias']};drc=json.load(open(P/'manifests/drc-pass2-large-v12.json'))['result'];delete=[]
for g in drc:
 if g['name']!='Clearance Error':continue
 for sub in g['list']:
  if sub['name']!='Hole to Hole':raise Exception('Unexpected clearance error')
  for e in sub['list']:
   a,b=[by[x] for x in e['objs']];assert a['net']==b['net'];dist=math.dist((a['x'],a['y']),(b['x'],b['y']))*.0254;assert dist<min(a['diameter'],b['diameter'])*.0254/2-.02
   delete.append(b['id']);print('Merge duplicate',b['net'],round(dist,3),'mm',b['id'])
guard=(P/'scripts/read-pcb-pads-v12.js').read_text().split('const out=')[0]
(P/'scripts/delete-duplicates-pass2-v12.js').write_text(guard+'return {deleted:await eda.pcb_PrimitiveVia.delete('+json.dumps(delete)+'),saved:await eda.pcb_Document.save()};',encoding='utf-8')
