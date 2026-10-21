import json
from pathlib import Path
r=json.load(open('PCB/manifests/context-completed-large-v12.json',encoding='utf-8'))['result'];print('Project',r['project']['friendlyName']);print('Board',r['board']['name'])
for b in r['project']['data']:
 for p in b['schematic']['page']:print('Page',p['uuid'],p['name'])
