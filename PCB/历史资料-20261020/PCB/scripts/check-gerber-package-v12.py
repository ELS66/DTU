from pathlib import Path
import json,re,zipfile,csv,math
P=Path('PCB');filename=P/'eda/DTU-V0.12-ML307R-DL-60x70-Gerber';report={};errors=[]
with zipfile.ZipFile(filename) as z:
 assert z.testzip() is None
 names=z.namelist();wanted=['Gerber_TopLayer.GTL','Gerber_BottomLayer.GBL','Gerber_InnerLayer1.G1','Gerber_InnerLayer2.G2','Gerber_BoardOutlineLayer.GKO','Drill_NPTH_Through.DRL','Drill_PTH_Through_Via.DRL']
 for n in wanted:
  if n not in names:errors.append('Missing '+n)
 outline=z.read('Gerber_BoardOutlineLayer.GKO').decode('ascii',errors='replace');print('Outline header',outline[:330]);print('Outline tail',outline[-900:])
 drill=z.read('Drill_NPTH_Through.DRL').decode('ascii',errors='replace');print('NPTH',drill[:2200])
 report={'zipEntries':len(names),'requiredFiles':wanted,'errors':errors,'outlineText':outline,'npthText':drill}
(P/'reports/Gerber内容核对-V0.12.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');assert not errors
