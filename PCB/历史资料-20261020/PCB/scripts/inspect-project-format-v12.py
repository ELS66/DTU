import zipfile,json,collections
z=zipfile.ZipFile('PCB/eda/DTU-V0.12-60x70-routing-stage.epro2');name=next(n for n in z.namelist() if n.endswith('.epru'));s=z.read(name).decode('utf-8');print(s[:1100]);rows=[]
for l in s.splitlines():
 if '||' not in l:continue
 h,b=l.split('||',1);h=json.loads(h);b=json.loads(b.rstrip('|')) if b.rstrip('|') else {};rows.append((h,b))
print('types',collections.Counter(h['type'] for h,b in rows))
for h,b in rows:
 if h['type'] in ['PROJECT','BOARD','SCH','SCHEMATIC','SCH_PAGE','DOCCATALOG','DOCTYPE','DOCHEAD']:print(h,str(b)[:550])
print('versionAttrs',[(h,b) for h,b in rows if h['type']=='ATTR' and b.get('key')=='Version'][:3])
