import json,sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8');j=json.loads(Path('PCB/docs/vendor/jlc-impedance-models.json').read_text(encoding='utf-8-sig'));print(list(j));models=j['body']['list'];print('models',len(models))
for m in models:
 if m.get('layerNumber')==1:print({k:v for k,v in m.items()if k not in ['createdBy','updatedBy']})
