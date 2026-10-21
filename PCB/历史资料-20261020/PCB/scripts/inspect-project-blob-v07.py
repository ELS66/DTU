import zipfile,json
from pathlib import Path
z=zipfile.ZipFile('PCB/eda/DTU-V0.6-精简完成.epro2');j=json.loads(z.read('project2.json'));print(list(j.keys()));
for k,v in j.items():print(k,str(v)[:800])
f=[n for n in z.namelist() if n.endswith('.epru')][0];b=z.read(f);print('epru',len(b),b[:150])
if b.startswith(b'PK'):
 import io
 zz=zipfile.ZipFile(io.BytesIO(b));print('nested',zz.namelist()[:20])
