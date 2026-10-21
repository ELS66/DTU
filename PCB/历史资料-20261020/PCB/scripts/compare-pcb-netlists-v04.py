import json,collections,sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8');P=Path('PCB');w=json.loads((P/'reports/pcb-netlist-jlceda-v04.json').read_text(encoding='utf-8-sig'))['result']['netlist'];(P/'reports/pcb-v04.net').write_text(w,encoding='utf-8');n=json.loads(w);s=json.loads((P/'reports/full-schematic-v04.net').read_text(encoding='utf-8'));print('PCB format keys',list(n));print('components',len(n.get('components',{})));by={c['props']['Designator']:c for c in n['components'].values()};diff=collections.defaultdict(list)
for uid,c in s['components'].items():
 r=c['props']['Designator'];p=by.get(r)
 if not p:print('MISSING',r);continue
 for k,v in c['props'].items():
  if p['props'].get(k)!=v:diff[k].append((r,v,p['props'].get(k)))
 for pn,pi in c['pinInfoMap'].items():
  if pi.get('net','')!=p['pinInfoMap'].get(pn,{}).get('net',''):print('PIN',r,pn,pi.get('net'),p['pinInfoMap'].get(pn))
print('propdiff counts',{k:len(v)for k,v in diff.items()});print('critical diffs',{k:v[:8]for k,v in diff.items()if k in ['Device','Footprint','Name','Unique ID','Channel ID','Add into BOM','Convert to PCB']});(P/'reports/pcb-schematic-property-differences-v04.json').write_text(json.dumps(diff,ensure_ascii=False,indent=2),encoding='utf-8')
