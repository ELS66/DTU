import sys,json
from pathlib import Path
from importlib.machinery import SourceFileLoader
p=Path('PCB');bridge=SourceFileLoader('dtu_bridge',str(p/'scripts/eda-v12.py')).load_module()
bridge.run((p/'scripts/guard-before-route-v13.js').read_text(encoding='utf8'),'manifests/guard-before-route-v13.json')
plan=json.loads((p/'manifests/connected-routing-v13.json').read_text(encoding='utf8'))
count=(len(plan['routes'])+len(plan['vias'])+29)//30
files=[p/f'scripts/apply-connected-routing-v13-{i}.js' for i in range(1,count+1)]
for i,f in enumerate(files):
 a=bridge.run(f.read_text(encoding='utf8'),'manifests/'+f.stem+'.json');print(i+1,len(files),len(a.get('ids',[])),a.get('saved'),flush=True)
