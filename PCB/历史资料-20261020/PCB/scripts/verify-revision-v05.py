import json,csv,collections
from pathlib import Path
p=Path('PCB');w=json.loads((p/'manifests/full-schematic-export-v05.json').read_text(encoding='utf-8-sig'));n=json.loads(w['result']['content']);(p/'reports/full-schematic-v05.net').write_text(json.dumps(n,ensure_ascii=False,indent=2),encoding='utf-8');plan=json.loads((p/'manifests/revision-v05.json').read_text(encoding='utf-8'));cs={};errors=[];count=0
for c in n['components'].values():
 r=c['props']['Designator']
 if r in cs:errors.append('duplicate '+r)
 cs[r]=c
if set(cs)!=set(plan['expected']):errors.append('Reference mismatch '+repr((set(plan['expected'])-set(cs),set(cs)-set(plan['expected']))))
for r,pins in plan['expected'].items():
 for k,net in pins.items():
  actual=cs.get(r,{}).get('pinInfoMap',{}).get(k,{}).get('net');count+=1
  if actual!=net:errors.append(f'{r}:{k} expected {net} actual {actual}')
for r,c in cs.items():
 for k,v in c['pinInfoMap'].items():
  if v.get('net') and k not in plan['expected'].get(r,{}):errors.append(f'Unexpected connection {r}:{k} {v["net"]}')
report={'status':'PASS' if not errors else 'FAIL','physicalComponents':len(cs),'pinNetAssertions':count,'counts':dict(collections.Counter(''.join(x for x in r if x.isalpha()) for r in cs)),'errors':errors}
(p/'reports/full-schematic-validation-v05.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=True))
with(p/'reports/BOM-V0.5.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['位号','数值/型号','厂商料号','供应商料号','默认装配'])
 for r,c in cs.items():
  a=c['props'];w.writerow([r,a.get('Name'),a.get('Manufacturer Part'),a.get('Supplier Part'),r not in plan['dnp']])
erc=json.loads((p/'reports/schematic-erc-v05.json').read_text(encoding='utf-8-sig'));print(json.dumps(erc.get('result'),ensure_ascii=True)[:1800])
