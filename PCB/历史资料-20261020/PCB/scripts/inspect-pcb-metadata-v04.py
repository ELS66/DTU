from pathlib import Path
import json,sys
sys.stdout.reconfigure(encoding='utf-8')
r=json.loads(Path('PCB/reports/pcb-source-records-v04.json').read_text(encoding='utf-8'));n=json.loads(Path('PCB/reports/full-schematic-v04.net').read_text(encoding='utf-8'))
for typ in ['COMPONENT','ATTR','RULE_TEMPLATE','RULE','LAYER_PHYS']:
 arr=[(h,v)for h,v in r if h['type']==typ];print(typ,arr[:3])
print('schematicexample',list(n['components'].items())[:1])

