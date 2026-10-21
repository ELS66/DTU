import json,csv,collections
from pathlib import Path
p=Path('PCB');plan=json.loads((p/'manifests/revision-v11.json').read_text(encoding='utf-8'));n=json.loads((p/'reports/full-schematic-v11.net').read_text(encoding='utf-8'));cs={};errors=[];count=0
for c in n['components'].values():
 r=c['props']['Designator']
 if r in cs:errors.append('Duplicate '+r)
 cs[r]=c
if set(cs)!=set(plan['expected']):errors.append('Reference mismatch')
for r,pins in plan['expected'].items():
 for k,net in pins.items():
  count+=1
  if cs.get(r,{}).get('pinInfoMap',{}).get(k,{}).get('net')!=net:errors.append(f'Wrong schematic net {r}:{k}')
for r,c in cs.items():
 for k,v in c['pinInfoMap'].items():
  if v.get('net') and k not in plan['expected'].get(r,{}):errors.append(f'Unexpected schematic connection {r}:{k}')
semantic={'U6':{'1':'RO','2':'RE','3':'DE','4':'DI','5':'GND','6':'A','7':'B','8':'VCC'},'U7':{'1':'C1+','2':'V+','3':'C1-','4':'C2+','5':'C2-','6':'V-','7':'DOUT2','8':'RIN2','9':'ROUT2','10':'DIN2','11':'DIN1','12':'ROUT1','13':'RIN1','14':'DOUT1','15':'GND','16':'VCC'},'U12':{'1':'A','2':'GND','3':'B','4':'Y','5':'VCC','6':'C'}}
semantic_checks=[]
for r,pins in semantic.items():
 for k,name in pins.items():
  actual=cs[r]['pinInfoMap'][k]['name'].upper().replace('~','').replace('/','').replace('\\','').replace('#','').replace('–','-')
  passed=actual==name
  if not passed:errors.append(f'Datasheet pin meaning {r}:{k} expected {name} actual {actual}')
  semantic_checks.append({'ref':r,'pin':k,'datasheetName':name,'libraryName':actual,'pass':passed})
for r,part in plan['changes'].items():
 if r.startswith('U') and cs[r]['props']['Manufacturer Part']!=part:errors.append('Wrong MPN '+r)
report={'status':'PASS' if not errors else 'FAIL','components':len(cs),'defaultAssembly':len(set(cs)-set(plan['dnp'])),'pinNetAssertions':count,'datasheetPinChecks':semantic_checks,'counts':dict(collections.Counter(''.join(z for z in r if z.isalpha()) for r in cs)),'errors':errors}
(p/'reports/schematic-validation-v11.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
with(p/'reports/BOM-V0.11.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['位号','数值/型号','厂商料号','供应商料号','默认装配'])
 for r,c in cs.items():
  a=c['props'];w.writerow([r,a.get('Name'),a.get('Manufacturer Part'),a.get('Supplier Part'),'否' if r in plan['dnp'] else '是'])
pcs=json.loads((p/'manifests/pcb-pads-interface-v11.json').read_text(encoding='utf-8-sig'))['result'];pe=[]
native=json.loads(json.loads((p/'manifests/pcb-netlist-interface-v11.json').read_text(encoding='utf-8-sig'))['result']['netlist']);ncs={c['props']['Designator']:c for c in native['components'].values()}
if set(ncs)!=set(cs):pe.append('Native PCB netlist reference mismatch')
for r,c in cs.items():
 for k in ['Unique ID','Name','Manufacturer Part','Device','Footprint','Channel ID']:
  if c['props'].get(k,'')!=ncs.get(r,{}).get('props',{}).get(k,''):pe.append(f'PCB property mismatch {r}:{k}')
if {c['ref'] for c in pcs}!=set(plan['expected']):pe.append('PCB reference mismatch')
for c in pcs:
 for q in c['pads']:
  if q['net']!=plan['expected'][c['ref']].get(q['number'],''):pe.append(f"Wrong PCB pad {c['ref']}:{q['number']}")
pcb={'status':'PASS' if not pe else 'FAIL','components':len(pcs),'physicalPads':sum(len(c['pads']) for c in pcs),'nettedPads':sum(bool(q['net']) for c in pcs for q in c['pads']),'nativeMetadataAssertions':len(cs)*6,'errors':pe}
(p/'reports/pcb-pad-validation-v11.json').write_text(json.dumps(pcb,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='datasheetPinChecks'},ensure_ascii=True));print(pcb)
if errors or pe:raise SystemExit(1)
