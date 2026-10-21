from pathlib import Path
import sqlite3,json
p=Path('PCB/eda/V0.12-final-60x70/DTU-V0.12-ML307R-DL-60x70.eprj2').resolve();c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True);r=c.execute("SELECT dataStr FROM documents WHERE uuid=?",('4211128ecf040c100b33238447713203',)).fetchone();s=r[0];print('data type',type(s),'length',len(s),'prefix',str(s)[:800])
try:
 j=json.loads(s);print('keys',list(j));
 for k,v in j.items():
  if 'PHYS' in k.upper() or 'LAYER' in k.upper():print(k,str(v)[:1500])
except json.JSONDecodeError:pass
