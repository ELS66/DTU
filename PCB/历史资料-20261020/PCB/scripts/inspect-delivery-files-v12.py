from pathlib import Path
import zipfile,json
P=Path('PCB/eda')
for name in ['DTU-V0.12-60x70-routing-stage.epro2','DTU-V0.12-positions-all','DTU-V0.12-ML307R-DL-60x70-Gerber']:
 p=P/name;print('\nFILE',name,'size',p.stat().st_size,'header',repr(p.read_bytes()[:60]))
 if zipfile.is_zipfile(p):
  with zipfile.ZipFile(p) as z:
   print('ZIP',z.namelist()[:24])
   if 'project2.json' in z.namelist():
    j=json.loads(z.read('project2.json'));print('META',list(j));print(str(j)[:2300])
 else:
  for enc in ['utf-8-sig','gb18030']:
   try:print(p.read_text(encoding=enc)[:800]);break
   except UnicodeDecodeError:continue
