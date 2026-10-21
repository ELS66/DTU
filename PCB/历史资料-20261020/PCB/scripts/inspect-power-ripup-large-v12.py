import json,math
from pathlib import Path
P=Path('PCB');a=json.load(open(P/'manifests/routing-resume-large-v12.json'))['result'];r=json.load(open(P/'manifests/escape-ripup-large-v12.json'))['removed']
for z in a['polys']:
 if z['id'] in r and z['net'] in ['VIN_485','VDD_3V3']:
  print(z['net'],z['id'],'widthMm',z['width']*.0254,'polyMm',[(v*.0254 if isinstance(v,(int,float)) else v) for v in z['polygon']])
