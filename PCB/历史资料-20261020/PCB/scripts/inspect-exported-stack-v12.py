import zipfile,json
from pathlib import Path
for file in ['DTU-V0.12-60x70-routing-stage.epro2','DTU-V0.12-ML307R-DL-60x70.epro2']:
 z=zipfile.ZipFile(Path('PCB/eda')/file);s=z.read(next(n for n in z.namelist() if n.endswith('.epru'))).decode('utf-8');current='';out=[]
 for l in s.splitlines():
  if '||' not in l:continue
  h,b=l.split('||',1);h=json.loads(h);b=json.loads(b.rstrip('|')) if b.rstrip('|') else {}
  if h['type']=='DOCHEAD':current=b['docType']
  if current=='PCB' and h['type']=='LAYER_PHYS':out.append((h,b))
 print(file,len(out),[(h['id'],b['thickness'],b['zIndex']) for h,b in out])
 print('Saved native header',Path('PCB/eda/V0.12-final-60x70/DTU-V0.12-ML307R-DL-60x70.eprj2').read_bytes()[:32])
