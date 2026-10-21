"""Move symmetric edge LEDs with the modules, and merge a duplicate same-net via."""
from pathlib import Path
import json,math
R=Path('PCB');M=R/'manifests';plan=json.loads((M/'clearancefix-rerouted-plan-v14.json').read_text(encoding='utf8'));ids=json.loads((M/'clearancefix-native-id-map-v14.json').read_text(encoding='utf8'));cs=json.loads((M/'clearancefix-staged-pads-v14.json').read_text(encoding='utf8'))['result']
delete='clearance_tail_via_0';v=next(v for v in plan['vias'] if v['id']==delete);keep=next(v for v in plan['vias'] if v['id']=='94c959e47d2e1bf2');changed=[]
for r in plan['routes']:
 altered=False
 for pt in r['pointsMm']:
  if r['net']=='GND' and math.dist(pt,(v['x'],v['y']))<.005:pt[:]=[keep['x'],keep['y']];altered=True
 if altered:changed.append(r)
plan['vias']=[q for q in plan['vias'] if q['id']!=delete]
refs=['D30','D31','D32','D33','D34','D35'];moves=[]
for c in cs:
 if c['ref'] not in refs:continue
 moves.append({'id':c['id'],'ref':c['ref'],'from':[c['x'],c['y']],'to':[c['x'],c['y']+2/.0254]});c['y']+=2/.0254
 for p in c['pads']:p['y']+=2/.0254
guard=(R/'scripts/read-clearancefix-source-v14.js').read_text(encoding='utf8').split('return {source:')[0]
args={'moves':moves,'deleteVia':ids['vias'][delete],'routes':[{'id':ids['routes'][r['id']],**{k:v for k,v in r.items() if k!='id'}} for r in changed]}
js=guard+'const a='+json.dumps(args)+";for(const m of a.moves){const c=await eda.pcb_PrimitiveComponent.get(m.id);if(!c||Math.abs(c.getState_Y()-m.from[1])>.01)throw Error('LED baseline changed');}for(const m of a.moves)if(!await eda.pcb_PrimitiveComponent.modify(m.id,{x:m.to[0],y:m.to[1]}))throw Error('LED move failed');if(!await eda.pcb_PrimitiveVia.delete(a.deleteVia))throw Error('Duplicate via deletion failed');for(const r of a.routes){const ps=r.pointsMm;const polygon=eda.pcb_MathPolygon.createPolygon([ps[0][0]/.0254,ps[0][1]/.0254,'L',...ps.slice(1).flatMap(p=>[p[0]/.0254,p[1]/.0254])]);if(!await eda.pcb_PrimitivePolyline.modify(r.id,{polygon,lineWidth:r.widthMm/.0254}))throw Error('Via merge tail failed');}return {leds:a.moves.map(m=>m.ref),mergedVia:a.deleteVia,routes:a.routes.map(r=>r.id),saved:await eda.pcb_Document.save()};"
(R/'scripts/apply-clearancefix-leds-v14.js').write_text(js,encoding='utf8')
(M/'clearancefix-rerouted-plan-v14.json').write_text(json.dumps(plan,indent=2),encoding='utf8');(M/'clearancefix-proposed-final-pads-v14.json').write_text(json.dumps({'result':cs},indent=2),encoding='utf8');(M/'clearancefix-led-via-finalization-v14.json').write_text(json.dumps(args,indent=2),encoding='utf8')
print('Prepared six edge LEDs +2mm, merged redundant GND via; drill wall minimum',min(math.dist((v['x'],v['y']),(w['x'],w['y']))-(v['hole']+w['hole'])/2 for i,v in enumerate(plan['vias']) for w in plan['vias'][:i]))
