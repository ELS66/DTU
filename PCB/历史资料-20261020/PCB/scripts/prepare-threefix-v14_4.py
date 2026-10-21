"""Repair array edge margin and align U.FL signal land to the manufacturer keepout."""
from pathlib import Path
import sys,json,zipfile,copy,datetime,shutil,base64,hashlib
sys.path.insert(0,str(Path('PCB/.tools').resolve()))
from shapely.geometry import Polygon,box,Point,LineString
from shapely.affinity import rotate,translate
R=Path('PCB');M=R/'manifests';E=R/'eda'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
s=(R/'scripts/package-silkclean-v13.py').read_text(encoding='utf8');exec(s[s.index('def rows('):s.index('before=rows(')]);exec(s[s.index('def active_project('):s.index('oldproj=active_project(')])
current=load(M/'current-pcb-delivery.json');assert 'V0.14.2' in current['revision']
assert rows(load(M/'threefix-before-source-v14_4.json')['result']['source'])==rows(load(M/current['actualSourceSnapshot'])['result']['source'])
backup=R/'backups'/('20261016-before-antenna-array-fix-'+datetime.datetime.now().strftime('%H%M%S'));backup.mkdir()
for p in [Path(current[k]) for k in ['nativeProject','productionGerber','deliveryArchive']]+[M/'current-pcb-delivery.json',M/'threefix-before-source-v14_4.json']:
 shutil.copy2(p,backup/p.name)
a=active_project(Path(current['nativeProject']));pcb=current['pcbUuid'];cs=load(M/'clearancefix-final-pads-v14.json')['result'];by={c['ref']:c for c in cs}
s=(R/'scripts/prepare-pinfix-v14_2.py').read_text(encoding='utf8');exec(s[s.index('def padgeom('):s.index('# Capture the actually exported stencil')])
exec((R/'scripts/render-hy20-gerber-v13.py').read_text(encoding='utf8').split('for label,copper,mask,silk in')[0])
z.close();z=zipfile.ZipFile(current['productionGerber']);cache.clear();paste=[g for g,d in geom('Gerber_TopPasteMaskLayer.GTP')[0] if d]
updates={};edits=[]
for k,p in a.items():
 if k[0]!='FOOTPRINT' or k[2]!='PAD':continue
 ref=None
 if k[1]==by['RN3']['footprint']['uuid'] and p['num'] in ['2','3','6','7']:ref='RN3'
 if k[1]==by['J5']['footprint']['uuid'] and p['num']=='2':ref='J5'
 if ref is None:continue
 q=copy.deepcopy(p);delta=0
 if ref=='RN3':q['defaultPad']['width']+=.04/.0254
 else:delta=.875-p['centerY']*.0254;q['centerY']=.875/.0254
 c=by[ref];oldworld=world(padgeom(p),c);hits=[g for g in paste if g.centroid.distance(oldworld.centroid)<.04];assert len(hits)==1
 pg=rotate(translate(hits[0],-c['x']*.0254,-c['y']*.0254),-c['rotation'],origin=(0,0));pg=translate(pg,0,delta)
 coords=list(pg.exterior.coords);path=[coords[0][0]/.0254,coords[0][1]/.0254,'L']+[v/.0254 for pt in coords[1:] for v in pt]
 fid=hashlib.sha256(('threefix-v14_4-paste-'+k[1]+'-'+k[3]).encode()).hexdigest()[:16]
 updates[('FOOTPRINT',k[1],'FILL',fid)]={'groupId':0,'netName':'','layerId':7,'width':0,'fillStyle':'SOLID','path':[path],'locked':True,'zIndex':600,'isBridgingCopper':False,'networkList':[],'refs':[]}
 exp=-min(q['defaultPad']['width'],q['defaultPad']['height'])/2-.01/.0254;q['topPasteExpansion']=exp;q['bottomPasteExpansion']=exp
 updates[k]=q;edits.append({'ref':ref,'footprint':k[1],'padId':k[-1],'pin':p['num'],'newBoundsLocalMm':list(padgeom(q).bounds),'oldBoundsLocalMm':list(padgeom(p).bounds),'pasteShiftLocalYmm':delta})
assert len(edits)==5
ob=[];newgs=[]
for c in cs:
 netmap={p['id'][len(c['id']):]:p['net'] for p in c['pads']}
 for k,p in a.items():
  if k[:3]!=('FOOTPRINT',c['footprint']['uuid'],'PAD') or p.get('layerId')!=1:continue
  q=(netmap[k[-1]],world(padgeom(updates.get(k,p)),c),c['ref']+'/'+p['num']);ob.append(q)
  if k in updates:newgs.append(q)
plan=load(M/current['actualCopperManifest'])
route_changes=[]
for t in plan['routes']:
 if t['id']!='53c42a1c6259f3d6':continue
 old=copy.deepcopy(t);pts=t['pointsMm'];t['pointsMm']=pts[:2]+[[12.8,68.7],[15.2,68.7],[15.4,68.5],[15.4,67.50000216]]+pts[2:]
 q=copy.deepcopy(a[('PCB',pcb,'POLY',t['id'])]);pts=t['pointsMm'];q['path']=[pts[0][0]/.0254,pts[0][1]/.0254,'L']+[v/.0254 for pt in pts[1:] for v in pt];updates[('PCB',pcb,'POLY',t['id'])]=q;route_changes.append({'before':old,'after':copy.deepcopy(t)})
for v in plan['vias']:ob.append((v['net'],Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=64),'via/'+v['id']))
for t in plan['routes']:
 if t['layer']==1:ob.append((t['net'],LineString(t['pointsMm']).buffer(t['widthMm']/2,quad_segs=64),'track/'+t['id']))
near=[]
for net,g,label in newgs:
 for on,og,other in ob:
  if net!=on and g.distance(og)<.152:near.append({'pad':label,'other':other,'gapMm':g.distance(og)})
for change in route_changes:
 t=change['after'];g=LineString(t['pointsMm']).buffer(t['widthMm']/2,quad_segs=64)
 for on,og,label in ob:
  if t['net']!=on and g.distance(og)<.152:near.append({'track':t['id'],'other':label,'gapMm':g.distance(og)})
(M/'threefix-expanded-copper-screen-v14_4.json').write_text(json.dumps({'changedInstances':len(newgs),'under0152mm':near},indent=2),encoding='utf8')
assert not near,near
zoneid=hashlib.sha256(b'threefix-J5-top-no-conductive-traces').hexdigest()[:16]
xy=[13.04999994,66.35001,'L',14.94999994,66.35001,14.94999994,68.45,13.04999994,68.45,13.04999994,66.35001]
updates[('PCB',pcb,'REGION',zoneid)]={'partitionId':'','groupId':0,'layerId':1,'width':0,'prohibitType':['COPPER'],'path':[[v/.0254 if isinstance(v,(int,float)) else v for v in xy]],'locked':True,'name':'J5_HIROSE_NO_TOP_COPPER','regionType':'PROHIBIT'}
writer=(R/'scripts/prepare-clearancefix-v14.py').read_text(encoding='utf8');exec(writer[writer.index('def write_project('):writer.index("if __name__=='__main__':")])
target=E/'DTU-V0.14.4-60x75-Threefix-input.epro2';write_project(current['nativeProject'],target,updates)
with zipfile.ZipFile(target) as zz:entries={n:zz.read(n) for n in zz.namelist()}
meta=json.loads(entries['project2.json']);meta['title']='DTU-V0.14.4-三处修正-60x75';entries['project2.json']=json.dumps(meta,ensure_ascii=False,indent=2).encode('utf8')
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as zz:
 for n,data in entries.items():zz.writestr(n,data)
folder=(R/'native-Threefix-final-v14_4').resolve();folder.mkdir(exist_ok=True)
js="if((await eda.dmt_Project.getCurrentProjectInfo())?.uuid!=='c6f0dcd7ccd611d978a8577b22693179724c4955797d2c0ce840c3bdc2ec674a')throw Error('Wrong source draft');await eda.pcb_Document.save();const f=new File([Uint8Array.from(atob("+json.dumps(base64.b64encode(target.read_bytes()).decode())+"),c=>c.charCodeAt(0))],'DTU-V0.14.4-60x75-Threefix.epro2');const imported=await eda.sys_FileManager.importProjectByProjectFile(f,'JLCEDA Pro',{importOption:'ImportDocument',associateFootprint:true,associate3DModel:true,importFootprintNotesLayer:true},{operation:'Offline Client Local Path',folderPath:"+json.dumps(str(folder))+"});if(!imported)throw Error('Import returned no project');return {imported};"
(R/'scripts/import-threefix-v14_4.js').write_text(js,encoding='utf8')
(M/'threefix-plan-v14_4.json').write_text(json.dumps({'baseline':current,'backupDirectory':str(backup.resolve()),'padMasterEdits':edits,'routeChanges':route_changes,'expandedInstances':len(newgs),'U2Unchanged':True,'J5DfmModelException':'Insulation-covered inner contact included in DFM model; do not expand copper into manufacturer no-trace area to satisfy its overlap ratio.'},ensure_ascii=False,indent=2),encoding='utf8')
(M/'threefix-actual-routing-v14_4.json').write_text(json.dumps(plan,indent=2),encoding='utf8')
print('Backup',backup,'master changes',len(edits),'affected instances',len(newgs))
