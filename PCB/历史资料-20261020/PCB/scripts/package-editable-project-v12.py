import json,zipfile,base64,csv,io,collections,hashlib
from pathlib import Path
P=Path('PCB');title='DTU-V0.12-ML307R-DL-60x70';src=P/'eda/DTU-V0.12-60x70-routing-stage.epro2';dst=P/'eda'/f'{title}.epro2'
changes=collections.Counter();pcb_before=[];pcb_after=[]
with zipfile.ZipFile(src) as zin,zipfile.ZipFile(dst,'w',zipfile.ZIP_DEFLATED) as zout:
 for n in zin.namelist():
  data=zin.read(n);newname=n
  if n=='project2.json':
   j=json.loads(data);j['title']=title;j['description']='ESP32-C5 + ML307R-DL，60×70mm，V0.12';data=json.dumps(j,ensure_ascii=False,separators=(',',':')).encode('utf-8')
  elif n.endswith('.epru'):
   current='';out=[]
   for l in data.decode('utf-8').splitlines(keepends=True):
    if '||' not in l:out.append(l);continue
    hh,bb=l.rstrip('\r\n').split('||',1);h=json.loads(hh);content=bb.rstrip('|');b=json.loads(content) if content else {};dirty=False
    if h['type']=='DOCHEAD':current=b['docType']
    if current=='PCB':pcb_before.append(l)
    if h['type']=='META' and current in ['BOARD','SCH','PCB']:
     b['title']='DTU_V0.12' if current=='SCH' else 'DTU_V0.12_60x70';dirty=True;changes['documentTitles']+=1
    if current=='SCH_PAGE' and h['type']=='ATTR':
     key=b.get('key');v=b.get('value')
     if key=='Version' and v=='V0.4':b['value']='V0.12';dirty=True;changes['version']+=1
     if key=='@Project Name' and v=='DTU-C5-Air780EPT-HW-V0.1-library':b['value']=title;dirty=True
     if key=='@Board Name' and v=='Board1':b['value']='DTU_V0.12_60x70';dirty=True
     if key=='@Schematic Name' and v=='Schematic1':b['value']='DTU_V0.12';dirty=True
    if dirty:l=hh+'||'+json.dumps(b,ensure_ascii=False,separators=(',',':'))+'|\n'
    if current=='PCB':pcb_after.append(l)
    out.append(l)
   data=''.join(out).encode('utf-8');newname=title+'.epru'
  zout.writestr(newname,data)
assert sum(a!=b for a,b in zip(pcb_before,pcb_after))==1,'Only the PCB title metadata may change'
assert zipfile.ZipFile(dst).testzip() is None
guard=(P/'scripts/read-pcb-pads-v12.js').read_text().split('const out=')[0]
encoded=base64.b64encode(dst.read_bytes()).decode('ascii')
code=guard+f"const raw=atob('{encoded}');const a=Uint8Array.from(raw,c=>c.charCodeAt(0));const f=new File([a],'{title}.epro2');const info=await eda.sys_FileManager.extractProjectInfo(f);if(info?.title!=='{title}')throw Error('Project title validation failed');return await eda.sys_FileManager.importProjectByProjectFile(f,'EasyEDA Pro',undefined,{{operation:'Offline Client Local Path',folderPath:'D:/DTU/PCB/eda/{title}'}});"
(P/'scripts/import-completed-project-v12.js').write_text(code,encoding='utf-8')
print('Packaged project',dst,changes,'bytes',dst.stat().st_size)
# Preserve native manufacturing export bytes, with conventional file extensions.
(P/'eda'/f'{title}-Gerber.zip').write_bytes((P/'eda'/f'{title}-Gerber').read_bytes())
raw=(P/'eda/DTU-V0.12-positions-all').read_bytes();txt=raw.decode('utf-16') if raw.startswith(b'\xff\xfe') else raw.decode('utf-8-sig');rows=list(csv.DictReader(io.StringIO(txt),delimiter='\t'));print('CPL columns',list(rows[0]),'rows',len(rows))
dnp=set(json.load(open(P/'manifests/revision-v12.json',encoding='utf-8'))['dnp']);assert len(rows)==159
for fname,filtered in [('DTU-V0.12-positions-all.csv',rows),('DTU-V0.12-positions-assembly.csv',[r for r in rows if r['Designator'] not in dnp])]:
 with (P/'eda'/fname).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(filtered)
 print(fname,len(filtered))
(P/'reports/project-package-v12.json').write_text(json.dumps({'title':title,'changes':changes,'epro2Sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'cplAllCount':len(rows),'cplAssemblyCount':len(rows)-len(dnp),'excludedAssembly':sorted(dnp)},ensure_ascii=False,indent=2),encoding='utf-8')
