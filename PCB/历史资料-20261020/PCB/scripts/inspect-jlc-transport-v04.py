from pathlib import Path
import re
for p in Path('PCB/docs/vendor').glob('jlc-*.js'):
 s=p.read_text(encoding='utf-8-sig')
 for pat in ['https://tools.jlc.com','shipHandle:','shipHandle)','baseURL:']:
  ms=list(re.finditer(re.escape(pat),s))
  for m in ms[:2]:print(p.name,pat,s[max(0,m.start()-220):m.end()+600])
