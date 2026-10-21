import json
from pathlib import Path
x=json.loads(Path('PCB/reports/pcb-rules-v04.json').read_text(encoding='utf-8-sig'))['result']['rules']['config'];print(json.dumps(x['Plane'])[:3000])
