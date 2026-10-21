import json
from pathlib import Path
P=Path('PCB');cs=json.loads((P/'reports/pcb-properties-v04.json').read_text(encoding='utf-8-sig'))['result'];print([{k:c[k]for k in ['ref','uid','other','footprint']}for c in cs if c['ref']in ['U1','U2','D1','R90']])
