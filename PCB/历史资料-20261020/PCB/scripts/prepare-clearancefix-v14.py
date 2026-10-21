"""Back up current release and stage a mechanically cleared, explicit-stencil revision."""
from pathlib import Path
import json,zipfile,copy,datetime,shutil,hashlib,base64,math,sys
sys.path.insert(0,str(Path('PCB/.tools').resolve()))
from shapely.geometry import LineString
from shapely.affinity import rotate,translate
R=Path('PCB');M=R/'manifests';E=R/'eda'
current=json.loads((M/'current-pcb-delivery-v13.json').read_text(encoding='utf8'))
s=(R/'scripts/package-silkclean-v13.py').read_text(encoding='utf8')
exec(s[s.index('def active_project('):s.index('oldproj=active_project(')])
a=active_project(Path(current['nativeProject']));pcb='4211128ecf040c100b33238447713203';fp='6b69a40d60760f97'
backup=R/'backups'/('20261016-before-clearancefix-'+datetime.datetime.now().strftime('%H%M%S'));backup.mkdir()
for p in [Path(current[k]) for k in ['nativeProject','productionGerber','deliveryArchive']]+[M/'current-pcb-delivery-v13.json',M/'clearancefix-before-live-source-v13.json']:
 shutil.copy2(p,backup/p.name)
cs=json.loads((M/'ml307fix-final-pads-v13.json').read_text(encoding='utf8'))['result']
shifts={c['id']:(0,3.2) for c in cs if c['y']*.0254>60}
shifts.update({c['id']:(0,2.0) for c in cs if c['ref'] in ['U1','U2']})
refs={c['id']:c['ref'] for c in cs};updates={};pad_edits=[]
for k,b in a.items():
 q=copy.deepcopy(b)
 if k[:2]==('FOOTPRINT',fp):
  if k[2]=='PAD':
   d=q['defaultPad'];w,h=d['width']*.0254,d['height']*.0254
   outer=w>2.5
   # 50 um nominal copper support on each edge; preserve the true metal model.
   d['width']=(w+.1)/.0254;d['height']=(h+.1)/.0254
   d['radius']=100*.05/((h+.1)/2) if outer else 0
   q['padOffsetX']=0;q['padOffsetY']=0
   q['topPasteExpansion']=(-.36 if outer else -.05)/.0254
   if outer:
    # Explicit, original 2.6 x 0.6 capsule stencil aperture; automatic paste is suppressed.
    g=translate(rotate(LineString([(-1,0),(1,0)]).buffer(.3,quad_segs=128),q['padAngle'],origin=(0,0)),q['centerX']*.0254,q['centerY']*.0254)
    coords=list(g.exterior.coords);path=[coords[0][0]/.0254,coords[0][1]/.0254,'L']+[v/.0254 for pt in coords[1:] for v in pt]
    fill={'groupId':0,'netName':'','layerId':7,'width':0,'fillStyle':'SOLID','path':[path],'locked':True,'zIndex':300,'isBridgingCopper':False,'networkList':[],'refs':[]}
    fid=hashlib.sha256(('v14-paste-'+k[-1]).encode()).hexdigest()[:16]
    updates[('FOOTPRINT',fp,'FILL',fid)]=fill
   pad_edits.append({'pin':q['num'],'outer':outer,'copperMm':[w+.1,h+.1],'pasteMm':[w,h]})
  elif k[2]=='META':
   q['title']='DTU_ML307R_DL_109_ENGINEERING_MARGIN_V14'
   q['description']='Engineering land adaptation from ML307R Hardware V1.0.1 Fig19/20. Copper +0.05mm per edge, outer R0.05; nominal solder paste preserved. Physical models unaltered. Not manufacturer-issued CAD; factory process approval pending.'
  elif k[2]=='ATTR' and b.get('key')=='Footprint':q['value']='DTU_ML307R_DL_109_ENGINEERING_MARGIN_V14'
 elif k[:2]==('PCB',pcb):
  if k[2]=='COMPONENT' and k[-1] in shifts:
   dx,dy=shifts[k[-1]];q['x']+=dx/.0254;q['y']+=dy/.0254
  elif k[2]=='ATTR' and b.get('parentId') in shifts:
   dx,dy=shifts[b['parentId']]
   if isinstance(q.get('x'),(int,float)):q['x']+=dx/.0254
   if isinstance(q.get('y'),(int,float)):q['y']+=dy/.0254
  elif k[2]=='META':q['title']='DTU_V0.14_单面贴装_60x75'
  elif k[2]=='POLY' and b.get('layerId')==11:
   q['path']=[0,0,'L',0,75/.0254,60/.0254,75/.0254,60/.0254,0,0,0]
  elif k[2]=='PAD' and b.get('hole'):
   if abs(b.get('centerY',0)*.0254-66)<.02:q['centerY']+=5/.0254
  elif k[2]=='POUR' and b.get('name') in ['GND_L2','GND_L3']:
   q['path']=[[.4/.0254,.4/.0254,'L',.4/.0254,74.6/.0254,59.6/.0254,74.6/.0254,59.6/.0254,.4/.0254,.4/.0254,.4/.0254]]
  elif k[2]=='POURED':q=None
 if q!=b:updates[k]=q

def write_project(source,target,edits):
 with zipfile.ZipFile(source) as z:
  name=next(n for n in z.namelist() if n.endswith('.epru'));blocks=[];block=[]
  for line in z.read(name).decode('utf8').splitlines():
   if '||' in line and json.loads(line.split('||',1)[0]).get('type')=='DOCHEAD':
    if block:blocks.append(block)
    block=[]
   block.append(line)
  if block:blocks.append(block)
  out=[]
  for block in blocks:
   out.extend(block);b=json.loads(block[0].split('||',1)[1].rstrip('|'));doc=(b['docType'],b['uuid'])
   ticket=max([json.loads(l.split('||',1)[0]).get('ticket',0) for l in block if '||' in l]+[0])
   for k,v in edits.items():
    if k[:2]!=doc:continue
    ticket+=1;body='|' if v is None else json.dumps(v,ensure_ascii=False,separators=(',',':'))
    out.append(json.dumps({'type':k[2],'id':k[3],'ticket':ticket},separators=(',',':'))+'||'+body+'|')
  with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as dest:
   for n in z.namelist():dest.writestr(n,('\n'.join(out)+'\n').encode('utf8') if n==name else z.read(n))

if __name__=='__main__':
 target=E/'DTU-V0.14-60x75-Clearancefix-input.epro2';write_project(current['nativeProject'],target,updates)
 folder=str((R/'native-Clearancefix-v14').resolve());Path(folder).mkdir(exist_ok=True)
 js='if((await eda.dmt_Project.getCurrentProjectInfo())?.uuid!=='+json.dumps(current['projectUuid'])+")throw Error('Wrong source project');const f=new File([Uint8Array.from(atob("+json.dumps(base64.b64encode(target.read_bytes()).decode())+"),c=>c.charCodeAt(0))],'DTU-V0.14-60x75-Clearancefix.epro2');return {imported:await eda.sys_FileManager.importProjectByProjectFile(f,'JLCEDA Pro',{importOption:'ImportDocument',associateFootprint:true,associate3DModel:true,importFootprintNotesLayer:true},{operation:'Offline Client Local Path',folderPath:"+json.dumps(folder)+"})};"
 (R/'scripts/import-clearancefix-v14.js').write_text(js,encoding='utf8')
 report={'backupDirectory':str(backup.resolve()),'sourceProject':current['projectUuid'],'inputProject':str(target.resolve()),'componentMoves':[{'id':i,'ref':refs[i],'deltaMm':list(d)} for i,d in shifts.items()],'boardMm':[60,75],'padEdits':pad_edits,'modelsUnchanged':True}
 (M/'clearancefix-stage-v14.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
 print('Backup:',backup,'component moves',len(shifts),'pad copper edits',len(pad_edits),'explicit stencil apertures',sum(p['outer'] for p in pad_edits))
