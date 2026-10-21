import json,sys,importlib.util
from pathlib import Path
P=Path('PCB');spec=importlib.util.spec_from_file_location('bridge',P/'scripts/eda-v12.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
for name in sys.argv[1:]:
 files=sorted((P/'scripts').glob('apply-'+name+'-*.js'),key=lambda p:int(p.stem.rsplit('-',1)[1]))
 if not files:raise Exception('No prepared batches '+name)
 for f in files:
  log=P/'manifests'/(f.stem+'-result.json')
  if log.exists():raise Exception('Already recorded; verify actual copper before replay '+str(f))
  r=b.run(f.read_text(encoding='utf8'),'manifests/'+log.name)
  print(f.name,'created',len(r['ids']),'saved',r['saved'],flush=True)
