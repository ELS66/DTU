import json,sys,math
from pathlib import Path
P=Path('PCB');name=sys.argv[1] if len(sys.argv)>1 else 'drc-pass2-large-v12.json';r=json.load(open(P/'manifests'/name,encoding='utf-8'))['result']
for group in r:
 print(group['name'],group.get('count'))
 for sub in group.get('list',[]):
  print(' ',sub['name'],sub.get('count'))
  if group['name']!='Connection Error':
   for err in sub['list']:print('  ',err.get('objs'),err.get('explanation',{}).get('param'))
