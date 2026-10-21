from pathlib import Path
import json
p=Path('PCB');n=len(json.loads((p/'manifests/power-routing-v07.json').read_text())['routes']);m=(n+39)//40
for f in (p/'scripts').glob('apply-power-routes-v07-*.js'):
 if int(f.stem.split('-')[-1])>m:f.unlink()
print('batches',m)
