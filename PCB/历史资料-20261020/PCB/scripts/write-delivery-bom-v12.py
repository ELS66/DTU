import json,csv,collections,re
from pathlib import Path
P=Path('PCB');raw=(P/'eda/DTU-V0.12-schematic-netlist').read_bytes()
for encoding in ['utf-8-sig','gb18030']:
 try:sch=json.loads(raw.decode(encoding));print('Netlist encoding',encoding);break
 except (UnicodeDecodeError,json.JSONDecodeError):continue
else:raise Exception('Cannot decode netlist')
(P/'reports/DTU-V0.12-schematic-netlist.json').write_text(json.dumps(sch,ensure_ascii=False,indent=2),encoding='utf-8')
cs=json.load(open(P/'manifests/pcb-pads-enlarged-v12.json',encoding='utf-8'))['result'];by={c['ref']:c for c in cs};dnp=set(json.load(open(P/'manifests/revision-v12.json',encoding='utf-8'))['dnp'])
groups=collections.defaultdict(list)
for c in sch['components'].values():
 pr=c['props'];ref=pr['Designator'];assert ref in by
 key=(pr.get('Name',''),pr.get('Manufacturer Part',''),pr.get('Supplier Part',''),pr.get('FootprintName',pr.get('Footprint','')),by[ref]['layer'],ref in dnp)
 groups[key].append(ref)
def refkey(r):m=re.match(r'([A-Za-z]+)(\d+)',r);return(m[1],int(m[2])) if m else(r,0)
with (P/'eda/DTU-V0.12-BOM.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['位号','数量','名称/参数','制造商型号','立创编号','封装','装配面','状态'])
 for k,refs in sorted(groups.items(),key=lambda z:refkey(min(z[1],key=refkey))):
  value,mpn,sku,fp,layer,optional=k;w.writerow([','.join(sorted(refs,key=refkey)),len(refs),value,mpn,sku,fp,'正面' if layer==1 else '背面','默认不装' if optional else '装配'])
print('BOM',len(groups),'rows',len(by),'parts','DNP',sorted(dnp))
errors=[];expected=json.load(open(P/'manifests/revision-v12.json',encoding='utf-8'))['expected']
for c in sch['components'].values():
 ref=c['props']['Designator']
 for pin,p in c['pinInfoMap'].items():
  if p.get('net','')!=expected[ref].get(pin,''):errors.append([ref,pin,p.get('net',''),expected[ref].get(pin,'')])
print('Netlist errors',errors)
assert not errors
