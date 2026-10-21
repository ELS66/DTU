from pathlib import Path
import json
P=Path('PCB');maps=json.loads((P/'manifests/full-schematic-netmap.json').read_text(encoding='utf-8'))
for ref in ['F1','U6','D6']:
 p=P/f'scripts/replace-protection-{ref}.js';s=p.read_text(encoding='utf-8');idx=s.index('await eda.sch_PrimitiveComponent.delete(old.getState_PrimitiveId());');s=s[:idx]+s[idx:].replace('return {ref:', 'const netmap='+json.dumps(maps[ref])+';for(const q of await c.getAllPins()){const net=netmap[q.getState_PinNumber()];if(!net)continue;const x=q.getState_X(),y=q.getState_Y(),r=q.getState_Rotation();const wire=await eda.sch_PrimitiveWire.create([x,y,x+Math.round(Math.cos(r*Math.PI/180))*20,y+Math.round(Math.sin(r*Math.PI/180))*20],net);if(!wire)throw Error("Reconnect failed "+q.getState_PinNumber());}return {ref:',1);p.write_text(s,encoding='utf-8')
m=json.loads((P/'manifests/design.json').read_text(encoding='utf-8'))
for a in m['parts']:
 if a.get('deviceUuid'):a['device']['uuid']=a['deviceUuid']
(P/'manifests/design.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
