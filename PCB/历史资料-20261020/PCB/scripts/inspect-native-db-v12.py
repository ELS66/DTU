import sqlite3,json
from pathlib import Path
p=Path('PCB/eda/V0.12-final-60x70/DTU-V0.12-ML307R-DL-60x70.eprj2').resolve();c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)
for name,sql in c.execute("SELECT name,sql FROM sqlite_master WHERE type='table'"):
 print(name,sql[:550])
