"""Back up and stage bounded land changes; keep all physical models and paste."""
from pathlib import Path
import json,zipfile,copy,datetime,shutil,hashlib,base64,sys,math
sys.path.insert(0,str(Path('PCB/.tools').resolve()))
from shapely.geometry import box,Polygon,Point,LineString
from shapely.affinity import rotate,translate
from shapely.ops import unary_union
R=Path('PCB');M=R/'manifests';E=R/'eda'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
s=(R/'scripts/package-silkclean-v13.py').read_text(encoding='utf8')
exec(s[s.index('def rows('):s.index('before=rows(')])
exec(s[s.index('def active_project('):s.index('oldproj=active_project(')])
current=load(M/'current-pcb-delivery.json')
assert 'V0.14.1' in current['revision']
live=rows(load(M/'pinfix-before-live-v14_2.json')['result']['source'])
assert live==rows(load(M/current['actualSourceSnapshot'])['result']['source'])
backup=R/'backups'/('20261016-before-pin-land-fix-'+datetime.datetime.now().strftime('%H%M%S'));backup.mkdir()
for p in [Path(current[k]) for k in ['nativeProject','productionGerber','deliveryArchive']]+[M/'current-pcb-delivery.json',M/'pinfix-before-live-v14_2.json']:
 shutil.copy2(p,backup/p.name)
a=active_project(Path(current['nativeProject']));pcb=current['pcbUuid']
cs=load(M/'clearancefix-final-pads-v14.json')['result'];by={c['ref']:c for c in cs}
fps={by[r]['footprint']['uuid']:r for r in ['U1','J4','D30']}
updates={};edits=[]
def padgeom(p):
 d=p['defaultPad'];w,h=d['width']*.0254,d['height']*.0254
 if d['padType']=='ELLIPSE':g=Point(0,0).buffer(1,quad_segs=64);from shapely.affinity import scale;g=scale(g,w/2,h/2)
 elif d['padType']=='RECT':
  rad=d.get('radius',0)*min(w,h)/200
  g=box(-w/2+rad,-h/2+rad,w/2-rad,h/2-rad).buffer(rad,quad_segs=64) if rad else box(-w/2,-h/2,w/2,h/2)
 elif d['padType']=='OVAL':g=LineString([(-max(0,w-h)/2,-max(0,h-w)/2),(max(0,w-h)/2,max(0,h-w)/2)]).buffer(min(w,h)/2,quad_segs=64)
 else:raise ValueError(d)
 return translate(rotate(g,p['padAngle'],origin=(0,0)),p['centerX']*.0254,p['centerY']*.0254)
def world(g,c):return translate(rotate(g,c['rotation'],origin=(0,0)),c['x']*.0254,c['y']*.0254)
# Capture the actually exported stencil, including any original global reduction.
exec((R/'scripts/render-hy20-gerber-v13.py').read_text(encoding='utf8').split('for label,copper,mask,silk in')[0])
z.close();z=zipfile.ZipFile(current['productionGerber']);cache.clear()
paste=[g for g,d in geom('Gerber_TopPasteMaskLayer.GTP')[0] if d]
for k,p in a.items():
 if k[0]!='FOOTPRINT' or k[1] not in fps or k[2]!='PAD':continue
 ref=fps[k[1]]
 if ref=='J4' and p['num'] not in ['C1','C2','C3','C5','C6','C7','CD']:continue
 q=copy.deepcopy(p);d=q['defaultPad']
 assert d['padType']=='RECT' and not d.get('radius',0)
 if ref=='U1':
  d['width']+=.04/.0254;d['height']+=.04/.0254
  reason='Engineering land +0.020 mm per edge, nominal lead models unchanged; based on Espressif v1.3 Fig10-2/11-2.'
 elif ref=='J4':
  assert q['padAngle']==0
  d['height']+=.13/.0254;q['centerY']-=.065/.0254
  reason='Engineering heel extension 0.13 mm, outer toe unchanged; SMN-303 drawing checked; nominal model retained.'
 else:
  d['width']+=.04/.0254;d['height']+=.04/.0254
  reason='Engineering land +0.020 mm per edge to support unchanged nominal LED termination model.'
 comp=by[ref];oldworld=world(padgeom(p),comp)
 candidates=[g for g in paste if g.centroid.distance(oldworld.centroid)<.04]
 assert len(candidates)==1,(ref,p['num'],len(candidates))
 pg=rotate(translate(candidates[0],-comp['x']*.0254,-comp['y']*.0254),-comp['rotation'],origin=(0,0))
 assert isinstance(pg,Polygon) and not pg.interiors
 coords=list(pg.exterior.coords);path=[coords[0][0]/.0254,coords[0][1]/.0254,'L']+[v/.0254 for xy in coords[1:] for v in xy]
 fid=hashlib.sha256(('pinfix-v14_2-paste-'+k[1]+'-'+k[3]).encode()).hexdigest()[:16]
 updates[('FOOTPRINT',k[1],'FILL',fid)]={'groupId':0,'netName':'','layerId':7,'width':0,'fillStyle':'SOLID','path':[path],'locked':True,'zIndex':500,'isBridgingCopper':False,'networkList':[],'refs':[]}
 exp=-(min(d['width'],d['height'])/2+.01/.0254)
 q['topPasteExpansion']=exp;q['bottomPasteExpansion']=exp
 updates[k]=q
 edits.append({'ref':ref,'footprint':k[1],'padId':k[3],'pin':p['num'],'oldBoundsLocalMm':list(padgeom(p).bounds),'newBoundsLocalMm':list(padgeom(q).bounds),'pasteBoundsLocalMm':list(pg.bounds),'reason':reason})
assert len(edits)==49
# Check all newly expanded copper against other-net pads, vias and existing tracks.
ob=[];newgs=[]
for c in cs:
 netmap={p['id'][len(c['id']):]:p['net'] for p in c['pads']}
 for k,p in a.items():
  if k[:3]!=('FOOTPRINT',c['footprint']['uuid'],'PAD'):continue
  if p.get('layerId')!=1:continue
  assert k[3] in netmap,(c['ref'],k)
  g=world(padgeom(updates.get(k,p)),c);item=(netmap[k[3]],g,c['ref']+'/'+p['num'])
  ob.append(item)
  if k in updates:newgs.append(item)
plan=load(M/'clearancefix-actual-routing-v14.json')
route_changes=[]
for t in plan['routes']:
 if t['id']!='fb2d950154672c84':continue
 old=copy.deepcopy(t);p=t['pointsMm']
 p[3][0]-=.04;p[4][0]-=.04;p[5][0]-=.04
 raw=copy.deepcopy(a[('PCB',pcb,'POLY',t['id'])])
 raw['path']=[p[0][0]/.0254,p[0][1]/.0254,'L']+[v/.0254 for xy in p[1:] for v in xy]
 updates[('PCB',pcb,'POLY',t['id'])]=raw
 route_changes.append({'before':old,'after':copy.deepcopy(t)})
for v in plan['vias']:ob.append((v['net'],Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=64),'via/'+v['id']))
for t in plan['routes']:
 if t['layer']==1:ob.append((t['net'],LineString(t['pointsMm']).buffer(t['widthMm']/2,quad_segs=64),'track/'+t['id']))
near=[]
for net,g,label in newgs:
 for on,og,other in ob:
  if net==on:continue
  gap=g.distance(og)
  if gap<.152:near.append({'pad':label,'other':other,'gapMm':gap,'net':net,'otherNet':on})
for change in route_changes:
 t=change['after'];g=LineString(t['pointsMm']).buffer(t['widthMm']/2,quad_segs=64)
 for on,og,other in ob:
  if t['net']!=on and g.distance(og)<.152:near.append({'track':t['id'],'other':other,'gapMm':g.distance(og)})
(M/'pinfix-expanded-copper-screen-v14_2.json').write_text(json.dumps({'changedInstances':len(newgs),'under0152mm':near},indent=2),encoding='utf8')
assert not near,near
# Append records to master footprints; never alter or remove the physical models.
writer=(R/'scripts/prepare-clearancefix-v14.py').read_text(encoding='utf8');exec(writer[writer.index('def write_project('):writer.index("if __name__=='__main__':")])
target=E/'DTU-V0.14.2-60x75-Pinfix-input.epro2';write_project(current['nativeProject'],target,updates)
folder=(R/'native-Pinfix-v14_2').resolve();folder.mkdir(exist_ok=True)
js="if((await eda.dmt_Project.getCurrentProjectInfo())?.uuid!=="+json.dumps(current['projectUuid'])+")throw Error('Wrong source project');await eda.pcb_Document.save();const f=new File([Uint8Array.from(atob("+json.dumps(base64.b64encode(target.read_bytes()).decode())+"),c=>c.charCodeAt(0))],'DTU-V0.14.2-60x75-Pinfix.epro2');return {imported:await eda.sys_FileManager.importProjectByProjectFile(f,'JLCEDA Pro',{importOption:'ImportDocument',associateFootprint:true,associate3DModel:true,importFootprintNotesLayer:true},{operation:'Offline Client Local Path',folderPath:"+json.dumps(str(folder))+"})};"
(R/'scripts/import-pinfix-v14_2.js').write_text(js,encoding='utf8')
report={'baseline':current,'backupDirectory':str(backup.resolve()),'padMasterEdits':edits,'routeChanges':route_changes,'expandedInstances':len(newgs),'physicalModelsUnchanged':True,'pastePreservedFromActualGerber':True,'pendingOtherModel':'J5 antenna soldered/floating metal definition needs manufacturer review; not changed blindly.'}
(M/'pinfix-actual-routing-v14_2.json').write_text(json.dumps(plan,indent=2),encoding='utf8')
(M/'pinfix-plan-v14_2.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('Backup',backup,'master pad changes',len(edits),'physical pad instances',len(newgs),'new copper conflicts',len(near))
