import json,zipfile
z=zipfile.ZipFile('PCB/eda/DTU-V0.12-60x70-routing-stage.epro2');s=z.read(next(n for n in z.namelist() if n.endswith('.epru'))).decode('utf-8');current=''
for l in s.splitlines():
 if '||' not in l:continue
 hh,bb=l.split('||',1);h=json.loads(hh);b=json.loads(bb.rstrip('|')) if bb.rstrip('|') else {}
 if h['type']=='DOCHEAD':current=b['docType']
 if h['type']=='META' and current in ['BOARD','SCH','SCH_PAGE','PCB']:print(current,str(b)[:1600])
