from pathlib import Path
import json,collections,csv
P=Path('PCB');n=json.loads((P/'reports/full-schematic-v04.net').read_text(encoding='utf-8'));m=json.loads((P/'manifests/design.json').read_text(encoding='utf-8'));expected=json.loads((P/'manifests/full-schematic-netmap.json').read_text(encoding='utf-8'));cs={};errors=[]
for uid,c in n['components'].items():
 r=c['props']['Designator']
 if r in cs:errors.append('Duplicate reference '+r)
 if not uid or not c['props'].get('Unique ID'):errors.append('Blank unique ID '+r)
 cs[r]=c
want={z['ref']for z in m['parts']}|{'U1','U2'}
if set(cs)!=want:errors.append('Reference mismatch '+repr((want-set(cs),set(cs)-want)))
count=0
for r,ps in expected.items():
 for p,net in ps.items():
  have=cs.get(r,{}).get('pinInfoMap',{}).get(p,{}).get('net')
  if have!=net:errors.append(f'{r}:{p} wanted {net}, got {have}')
  count+=1
for z in m['parts']:
 if z.get('supplierId') and cs[z['ref']]['props'].get('Supplier Part')!=z['supplierId']:errors.append('SKU mismatch '+z['ref'])
report={'status':'PASS'if not errors else'FAIL','physicalComponents':len(cs),'pinNetAssertions':count,'errors':errors,'scope':'Actual exported schematic nets and BOM IDs; hardware tests and PCB checks separate'}
(P/'reports/full-schematic-validation-v04.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report))
(P/'reports/auto-selector.net').write_text(json.dumps(n,ensure_ascii=False,indent=2),encoding='utf-8')
with (P/'reports/BOM-V0.4.csv').open('w',encoding='utf-8-sig',newline='')as f:
 w=csv.writer(f);w.writerow(['位号','数值/型号','厂商料号','供应商料号','封装','默认装配'])
 for r,c in cs.items():
  p=c['props'];z=next((z for z in m['parts']if z['ref']==r),{})
  w.writerow([r,p.get('Name',''),p.get('Manufacturer Part',''),p.get('Supplier Part',''),z.get('footprint',p.get('Footprint','')),not z.get('dnp',False)])
