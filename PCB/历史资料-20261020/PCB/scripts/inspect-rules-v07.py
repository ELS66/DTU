import json
from pathlib import Path
r=json.loads(Path('PCB/reports/pcb-rules-v04.json').read_text(encoding='utf-8-sig'))['result']['rules']['config'];print('keys',list(r));print(json.dumps(r.get('Copper',{}))[:3000]);print('physicskeys',list(r['Physics']))
