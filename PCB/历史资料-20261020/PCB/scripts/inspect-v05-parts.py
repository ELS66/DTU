import json
from pathlib import Path
p=Path('PCB'); w=json.loads((p/'manifests/schematic-before-v05.json').read_text(encoding='utf-8-sig')); n=json.loads(w['result']['content']); (p/'reports/schematic-before-v05.net').write_text(json.dumps(n,ensure_ascii=False,indent=2),encoding='utf-8')
for c in n['components'].values():
 a=c['props']; page=a.get('Channel ID','').split('I')[0]
 if page in ['$6','$7'] or a['Designator'] in ['R120','R102','R103','R105','C70','C71']:
  print(a['Designator'],a.get('Name'),a.get('Device'),a.get('Supplier Part'),page)
