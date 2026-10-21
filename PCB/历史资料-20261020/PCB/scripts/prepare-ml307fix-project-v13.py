from pathlib import Path
import json,zipfile,collections,datetime,shutil,hashlib,copy,base64,math
R=Path('PCB');M=R/'manifests';E=R/'eda';current=json.loads((M/'current-pcb-delivery-v13.json').read_text(encoding='utf8'))
backup=R/'backups'/('20261016-before-ML307-footprint-fix-'+datetime.datetime.now().strftime('%H%M%S'));backup.mkdir()
for p in [Path(current[k]) for k in ['nativeProject','productionGerber','deliveryArchive']]+[M/'current-pcb-delivery-v13.json',M/'ml307fix-before-source-v13.json']:shutil.copy2(p,backup/p.name)
(M/'ml307fix-backup-v13.json').write_text(json.dumps({'directory':str(backup.resolve())},indent=2))
# Keep pad IDs, pin numbers and nets. Revise the master; import under a new native project for cache consistency.
code=(R/'scripts/package-silkclean-v13.py').read_text(encoding='utf8');exec(code[code.index('def active_project('):code.index('oldproj=active_project(')])
a=active_project(Path(current['nativeProject']));fp='6b69a40d60760f97';fprows={k[-1]:(k,b) for k,b in a.items() if k[0]=='FOOTPRINT' and k[1]==fp and isinstance(b,dict)}
updates={};padtargets=[];phys=json.loads((M/'u2-ml307-physical-reference-review-v13.json').read_text(encoding='utf8'))['physicalPads'];model=json.loads((M/'u2-pin-boundary-library-audit-v13.json').read_text(encoding='utf8'))['rows'];byid={r['modelId']:r for r in model}
for k,b in a.items():
 if k[0]!='FOOTPRINT' or k[1]!=fp or not isinstance(b,dict):continue
 q=copy.deepcopy(b)
 if k[2]=='PAD':
  q['centerX']=round(b['centerX']*.0254,2)/.0254;q['centerY']=round(b['centerY']*.0254,2)/.0254
  if abs(b['defaultPad']['width']*.0254-1.8)<.002:
   ang=math.radians(b['padAngle']);ux,uy=round(math.cos(ang)),round(math.sin(ang));sign=1 if b['centerX']*ux+b['centerY']*uy>0 else -1
   q['centerX']+=.4*sign*ux/.0254;q['centerY']+=.4*sign*uy/.0254;q['defaultPad']={'padType':'RECT','width':2.6/.0254,'height':.6/.0254,'radius':.3/.0254};padtargets.append({'pin':b['num'],'id':k[-1],'centerMm':[q['centerX']*.0254,q['centerY']*.0254],'angle':b['padAngle'],'sizeMm':[2.6,.6],'radiusMm':.3})
  else:
   q['defaultPad']['width']=round(b['defaultPad']['width']*.0254,2)/.0254;q['defaultPad']['height']=round(b['defaultPad']['height']*.0254,2)/.0254
 elif b.get('layerId')==50 and 'path' in b:
  item=next(p for p in phys if p['pin']==byid[k[-1]]['pin']);x0,y0,x1,y1=item['manufacturerNominalPhysicalBoundsMm'];q['path']=[[x0/.0254,y0/.0254,'L',x1/.0254,y0/.0254,x1/.0254,y1/.0254,x0/.0254,y1/.0254,x0/.0254,y0/.0254]]
 elif k[2]=='META':q['title']='DTU_ML307R_DL_LCC48_LGA61_OFFICIAL_V1_0_1';q['description']='ML307R-DL dedicated land pattern; OneMO AT Hardware V1.0.1 Fig19/20; outer2.6x0.6 R0.3; physical lead model corrected. Assembly still requires factory verification.'
 elif k[2]=='ATTR' and b.get('key')=='Footprint':q['value']='DTU_ML307R_DL_LCC48_LGA61_OFFICIAL_V1_0_1'
 if q!=b:updates[k]=q
# Native 4.1 append-only records, per-document logical clocks.
z=zipfile.ZipFile(current['nativeProject']);name=next(n for n in z.namelist() if n.endswith('.epru'));blocks=[];block=[]
for line in z.read(name).decode('utf8').splitlines():
 if line.startswith('{"type":"DOCHEAD"') or (line.startswith('{') and '||' in line and json.loads(line.split('||',1)[0]).get('type')=='DOCHEAD'):
  if block:blocks.append(block);block=[]
 block.append(line)
if block:blocks.append(block)
out=[]
for block in blocks:
 out.extend(block);h,b=block[0].split('||',1);b=json.loads(b.rstrip('|'));doc=(b['docType'],b['uuid']);ticket=max([json.loads(l.split('||',1)[0]).get('ticket',0) for l in block if '||' in l]+[0])
 for k,v in updates.items():
  if k[:2]!=doc:continue
  ticket+=1;out.append(json.dumps({'type':k[2],'id':k[3],'ticket':ticket},separators=(',',':'))+'||'+json.dumps(v,ensure_ascii=False,separators=(',',':'))+'|')
target=E/'DTU-V0.13-60x70-ML307fix-input.epro2'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as q:
 for n in z.namelist():q.writestr(n,('\n'.join(out)+'\n').encode('utf8') if n==name else z.read(n))
z.close();(M/'ml307fix-master-edits-v13.json').write_text(json.dumps({'master':fp,'changes':dict(collections.Counter(k[2] for k in updates)),'outerPads':padtargets,'backup':str(backup.resolve())},indent=2),encoding='utf8')
folder=str((R/'native-ML307fix').resolve());Path(folder).mkdir(exist_ok=True)
js="if((await eda.dmt_Project.getCurrentProjectInfo())?.uuid!=="+json.dumps(current['projectUuid'])+")throw Error('Wrong source project');const b64="+json.dumps(base64.b64encode(target.read_bytes()).decode())+";const f=new File([Uint8Array.from(atob(b64),c=>c.charCodeAt(0))],'DTU-V0.13-60x70-ML307fix.epro2');return {imported:await eda.sys_FileManager.importProjectByProjectFile(f,'JLCEDA Pro',{importOption:'ImportDocument',associateFootprint:true,associate3DModel:true,importFootprintNotesLayer:true},{operation:'Offline Client Local Path',folderPath:"+json.dumps(folder)+"})};"
(R/'scripts/import-ml307fix-native-v13.js').write_text(js,encoding='utf8');print('Backup',backup,'Master edits',collections.Counter(k[2] for k in updates))
