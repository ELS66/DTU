import json
from pathlib import Path
x=json.loads(Path('PCB/manifests/power-layout-v07.json').read_text());print({k:v for k,v in x['positions'].items() if k in ['R92','R93','C108','C109','D14','U11']})
