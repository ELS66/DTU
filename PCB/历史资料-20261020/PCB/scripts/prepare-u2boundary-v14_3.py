"""Support real ML307 nominal metal and the current C48982537 DFM mesh."""
from pathlib import Path
import json,zipfile,sys,copy,datetime,shutil,base64,math
sys.path.insert(0,str(Path('PCB/.tools').resolve()))
from shapely.geometry import Polygon,box,Point,LineString
from shapely.affinity import rotate,translate
R=Path('PCB');M=R/'manifests';E=R/'eda'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
s=(R/'scripts/package-silkclean-v13.py').read_text(encoding='utf8');exec(s[s.index('def rows('):s.index('before=rows(')]);exec(s[s.index('def active_project('):s.index('oldproj=active_project(')])
current=load(M/'current-pcb-delivery.json');assert 'V0.14.2' in current['revision']
assert rows(load(M/'u2boundary-before-v14_3.json')['result']['source'])==rows(load(M/current['actualSourceSnapshot'])['result']['source'])
backup=R/'backups'/('20261016-before-u2-dfm-boundary-'+datetime.datetime.now().strftime('%H%M%S'));backup.mkdir()
for p in [Path(current[k]) for k in ['nativeProject','productionGerber','deliveryArchive']]+[M/'current-pcb-delivery.json',M/'u2boundary-before-v14_3.json']:
 shutil.copy2(p,backup/p.name)
a=active_project(Path(current['nativeProject']));fp='6b69a40d60760f97';pcb=current['pcbUuid'];updates={};edits=[]
cs=load(M/'clearancefix-final-pads-v14.json')['result'];by={q['ref']:q for q in cs}
s=(R/'scripts/prepare-pinfix-v14_2.py').read_text(encoding='utf8');exec(s[s.index('def padgeom('):s.index('# Capture the actually exported stencil')])
for k,p in a.items():
 if k[:3]!=('FOOTPRINT',fp,'PAD'):continue
 q=copy.deepcopy(p);d=q['defaultPad'];w,h=d['width']*.0254,d['height']*.0254
 outer=w>2.5;central=abs(w-1.4)<.001 and abs(h-1.4)<.001
 if outer:
  d['height']+=.10/.0254;d['radius']=100*.05/((h+.10)/2)
  q['topPasteExpansion']=-(h+.10)/2/.0254-.01/.0254;q['bottomPasteExpansion']=q['topPasteExpansion']
 elif central:
  d['width']+=.10/.0254;d['height']+=.10/.0254
  q['topPasteExpansion']-=.05/.0254;q['bottomPasteExpansion']-=.05/.0254
 else:
  d['width']+=.04/.0254;d['height']+=.04/.0254
  q['topPasteExpansion']-=.02/.0254;q['bottomPasteExpansion']-=.02/.0254
 updates[k]=q;edits.append({'pin':q['num'],'padId':k[-1],'outer':outer,'oldMm':[w,h],'newMm':[d['width']*.0254,d['height']*.0254]})
assert len(edits)==109
ob=[];newgs=[]
for c in cs:
 netmap={p['id'][len(c['id']):]:p['net'] for p in c['pads']}
 for k,p in a.items():
  if k[:3]!=('FOOTPRINT',c['footprint']['uuid'],'PAD') or p.get('layerId')!=1:continue
  g=world(padgeom(updates.get(k,p)),c);q=(netmap[k[3]],g,c['ref']+'/'+p['num']);ob.append(q)
  if k in updates:newgs.append(q)
plan=load(M/current['actualCopperManifest'])
route_changes=[]
for t in plan['routes']:
 if t['id'] not in ['85f1f88e6f3b6920','a6e8fb4f01680569']:continue
 old=copy.deepcopy(t)
 if t['id']=='85f1f88e6f3b6920':t['pointsMm'][18][0]-=.05;t['pointsMm'][19][0]-=.05
 else:t['pointsMm'][1][0]+=.05
 raw=copy.deepcopy(a[('PCB',pcb,'POLY',t['id'])]);p=t['pointsMm']
 raw['path']=[p[0][0]/.0254,p[0][1]/.0254,'L']+[v/.0254 for pt in p[1:] for v in pt]
 updates[('PCB',pcb,'POLY',t['id'])]=raw;route_changes.append({'before':old,'after':copy.deepcopy(t)})
for v in plan['vias']:ob.append((v['net'],Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=64),'via/'+v['id']))
for t in plan['routes']:
 if t['layer']==1:ob.append((t['net'],LineString(t['pointsMm']).buffer(t['widthMm']/2,quad_segs=64),'track/'+t['id']))
near=[]
for net,g,label in newgs:
 for on,og,other in ob:
  if net!=on and g.distance(og)<.152:near.append({'pad':label,'other':other,'gapMm':g.distance(og),'net':net,'otherNet':on})
for change in route_changes:
 t=change['after'];g=LineString(t['pointsMm']).buffer(t['widthMm']/2,quad_segs=64)
 for on,og,label in ob:
  if t['net']!=on and g.distance(og)<.152:near.append({'track':t['id'],'other':label,'gapMm':g.distance(og)})
(M/'u2boundary-expanded-copper-screen-v14_3.json').write_text(json.dumps({'edits':edits,'under0152mm':near},indent=2),encoding='utf8')
assert not near,near
writer=(R/'scripts/prepare-clearancefix-v14.py').read_text(encoding='utf8');exec(writer[writer.index('def write_project('):writer.index("if __name__=='__main__':")])
target=E/'DTU-V0.14.3-60x75-U2fix-input.epro2';write_project(current['nativeProject'],target,updates)
folder=(R/'native-U2fix-v14_3').resolve();folder.mkdir(exist_ok=True)
js="if((await eda.dmt_Project.getCurrentProjectInfo())?.uuid!=='778f520ce68ec55093c846023b96e6c8ebd08057c8fcf39cccecb2d8dc791848')throw Error('Wrong source draft');await eda.pcb_Document.save();const f=new File([Uint8Array.from(atob("+json.dumps(base64.b64encode(target.read_bytes()).decode())+"),c=>c.charCodeAt(0))],'DTU-V0.14.3-60x75-U2fix.epro2');return {imported:await eda.sys_FileManager.importProjectByProjectFile(f,'JLCEDA Pro',{importOption:'ImportDocument',associateFootprint:true,associate3DModel:true,importFootprintNotesLayer:true},{operation:'Offline Client Local Path',folderPath:"+json.dumps(str(folder)+'-all109')+"})};"
(R/'scripts/import-u2boundary-v14_3.js').write_text(js,encoding='utf8')
(M/'u2boundary-plan-v14_3.json').write_text(json.dumps({'baseline':current,'backupDirectory':str(backup.resolve()),'padEdits':edits,'routeChanges':route_changes,'physicalModelEdits':0,'schematicEdits':0,'pasteIntendedUnchanged':True},ensure_ascii=False,indent=2),encoding='utf8')
(M/'u2boundary-actual-routing-v14_3.json').write_text(json.dumps(plan,indent=2),encoding='utf8')
print('Backup',backup,'109 pad changes; preflight passed')
