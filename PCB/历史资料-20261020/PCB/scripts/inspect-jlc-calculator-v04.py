from pathlib import Path
import re
for p in Path('PCB/docs/vendor').glob('jlc-*.js'):
 s=p.read_text(encoding='utf-8-sig');hits=list(re.finditer('impedance|Impedance',s))
 if hits:
  print(p.name,len(hits))
  for m in hits[:8]:print(s[max(0,m.start()-150):m.end()+230])
