import zipfile,json
z=zipfile.ZipFile('PCB/eda/DTU-V0.6-精简完成.epro2');s=z.read(next(n for n in z.namelist() if n.endswith('.epru'))).decode('utf-8');active=False;rec=[]
for line in s.splitlines():
 if '||' not in line:continue
 a,b=line.split('||',1)
 try:h=json.loads(a);v=json.loads(b.rstrip('|'))
 except:continue
 if h['type']=='DOCHEAD':active=v.get('uuid')=='a0d35b9d3425b69a'
 if active:
  rec.append((h,v))
  if h['type'] in ['REGION','SLOT','HOLE','SOLIDREGION'] or h.get('id')=='e68':print(h,v)
print('SIM footprint records',len(rec))
from pathlib import Path
Path('PCB/manifests/sim-footprint-v07.json').write_text(json.dumps(rec,indent=2))
