import json,math
from pathlib import Path
P=Path('PCB');pcs=json.load(open(P/'manifests/pcb-pads-release-v12.json',encoding='utf-8'))['result'];sch=json.loads((P/'eda/DTU-V0.12-schematic-netlist').read_text(encoding='utf-8-sig'));expected=json.load(open(P/'manifests/revision-v12.json',encoding='utf-8'))['expected'];errors=[];count=0
assert len(pcs)==len(sch['components'])==len(expected)==159
for c in pcs:
 for p in c['pads']:
  if p['net']!=expected[c['ref']].get(p['number'],''):errors.append(['PCB',c['ref'],p['number'],p['net']])
for c in sch['components'].values():
 ref=c['props']['Designator']
 for number,p in c['pinInfoMap'].items():
  count+=1
  if p.get('net','')!=expected[ref].get(number,''):errors.append(['SCH',ref,number,p.get('net','')])
pcb_drc=json.load(open(P/'manifests/drc-release-v12.json'))['result'];sch_drc=json.load(open(P/'manifests/schematic-drc-release-v12.json'))['result'];warnings=sum(len(g.get('primitives',[])) for g in sch_drc if g.get('type')=='warn');scherrors=[g for g in sch_drc if g.get('type')!='warn']
if pcb_drc:errors.append(['PCB DRC',len(pcb_drc)])
if scherrors:errors.append(['SCH DRC',scherrors])
report={'status':'PASS' if not errors else 'FAIL','projectUuid':'da9775b4e341e163260ddd9bb097311369dc525f008e7fcc093462a87b61a989','pcbComponents':len(pcs),'pcbPads':sum(len(c['pads']) for c in pcs),'schematicComponents':len(sch['components']),'schematicPinAssertions':count,'pcbDrcErrorGroups':len(pcb_drc),'schematicErrorGroups':len(scherrors),'schematicAttributeWarnings':warnings,'errors':errors}
(P/'reports/最终工程核对-V0.12.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(report);assert not errors
