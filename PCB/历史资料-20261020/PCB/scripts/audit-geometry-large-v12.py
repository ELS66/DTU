import json,math
from pathlib import Path
P=Path('PCB');plan=json.load(open(P/'manifests/revision-v12.json',encoding='utf8'));cs=json.load(open(P/'manifests/pcb-pads-enlarged-v12.json',encoding='utf8'))['result'];by={c['ref']:c for c in cs};sch=json.loads(json.load(open(P/'manifests/schematic-after-v12.json',encoding='utf8'))['result']['content']);schby={c['props']['Designator']:c for c in sch['components'].values()}
errors=[]
if set(by)!=set(plan['expected']):errors.append('PCB designator set differs from expected')
for ref,e in plan['expected'].items():
 for p in by[ref]['pads']:
  if p['net']!=e.get(p['number'],''):errors.append([ref,p['number'],p['net'],e.get(p['number'],'')])
 for pin,net in schby[ref]['pinInfoMap'].items():
  actual=net.get('net','') if isinstance(net,dict) else net
  if actual!=e.get(pin,''):errors.append(['SCH',ref,pin,actual,e.get(pin,'')])
pitch={}
for ref in ['J1','J2','J3','J6','J7']:
 ps=sorted(by[ref]['pads'],key=lambda p:p['x']);ds=[math.dist((a['x']*.0254,a['y']*.0254),(b['x']*.0254,b['y']*.0254)) for a,b in zip(ps,ps[1:])];pitch[ref]=ds
 expected=2.0 if ref in ['J1','J2','J3'] else 2.54
 if any(abs(x-expected)>.004 for x in ds):errors.append('Pitch '+ref)
for a,b in [('D30','D33'),('D31','D34'),('D32','D35')]:
 if abs((by[a]['x']+by[b]['x'])*.0254-60)>.002 or abs((by[a]['y']-by[b]['y'])*.0254)>.002:errors.append('LED symmetry '+a)
if abs((by['J6']['y']-by['J7']['y'])*.0254)>.002:errors.append('Download row')
report={'pcbComponents':len(by),'schematicComponents':len(schby),'pcbPads':sum(len(c['pads']) for c in cs),'pitchMm':pitch,'errors':errors}
(P/'reports/器件网络与机械核对-V0.12.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(report)
