from pathlib import Path
import zipfile,json,re
p=Path('PCB');f=p/'eda/DTU-V0.6-精简完成.epro2';print('backupZip',zipfile.is_zipfile(f))
if zipfile.is_zipfile(f):
 with zipfile.ZipFile(f) as z:print('backupIntegrity',z.testzip(),'files',len(z.namelist()))
for name in ['README.md','DTU主板硬件设计与API绘板规范.md','reports/V0.6精简与验证记录.md']:
 q=p/name;missing=[]
 for link in re.findall(r'\]\(([^)]+)\)',q.read_text(encoding='utf-8-sig')):
  if not link.startswith(('https://','http://')) and not (q.parent/link).exists():missing.append(link)
 print(name,'missingLinks',missing)
for name in ['full-schematic-validation-v06.json','pcb-pad-validation-v06.json','pcb-drc-summary-v06.json']:
 print(name,(p/'reports'/name).read_text()[:400])
