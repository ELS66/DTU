import sys,importlib
from pathlib import Path
sys.path.insert(0,'PCB/scripts');e=importlib.import_module('eda-v12')
for p in sorted(Path('PCB/scripts').glob('apply-reference-planes-v12-*.js'),key=lambda p:int(p.stem.split('-')[-1])):
 r=e.run(p.read_text(),f'manifests/{p.stem}.json');print(p.name,len(r['ids']),flush=True)
