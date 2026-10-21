from pathlib import Path
import json,collections
P=Path('PCB');lines=(P/'reports/pcb-v04.epcb').read_text(encoding='utf-8-sig').splitlines();records=[]
for line in lines:
 if not line.strip():continue
 h,v=line.split('||',1);records.append((json.loads(h),json.loads(v.rstrip('|'))))
print(collections.Counter(h['type']for h,v in records))
for h,v in records:
 if h['type']in ['NETLIST','NET','NETS','DOCHEAD','CANVAS','ATTR','PAD_NET']:
  if h['type']=='ATTR' and v.get('key')not in ['Unique ID']:continue
  print(h,str(v)[:700])
  if h['type']=='PAD_NET':break
(P/'reports/pcb-source-records-v04.json').write_text(json.dumps(records),encoding='utf-8')
