"""Write the routed native project with persistent footprint stencil settings."""
from pathlib import Path
import json,zipfile,copy,base64,hashlib
R=Path('PCB');M=R/'manifests';E=R/'eda'
s=(R/'scripts/package-silkclean-v13.py').read_text(encoding='utf8');exec(s[s.index('def active_project('):s.index('oldproj=active_project(')])
s=(R/'scripts/prepare-clearancefix-v14.py').read_text(encoding='utf8');exec(s[s.index('def write_project('):s.index("if __name__=='__main__':")])
source=E/'DTU-V0.14-60x75-Clearancefix.epro2';a=active_project(source);pcb='4211128ecf040c100b33238447713203';fp='6b69a40d60760f97';edits={}
plan=json.loads((M/'clearancefix-rerouted-plan-v14.json').read_text(encoding='utf8'));route_ids={};via_ids={}
for k,b in a.items():
 if k[:2]==('PCB',pcb) and k[2]=='POLY' and b.get('layerId') in [1,2,15,16] and b.get('netName'):edits[k]=None
 if k[:3]==('FOOTPRINT',fp,'PAD'):
  q=copy.deepcopy(b);q['bottomPasteExpansion']=q['topPasteExpansion'];q['topSolderExpansion']=2;q['bottomSolderExpansion']=2
  edits[k]=q
for i,r in enumerate(plan['routes']):
 rid=r['id'] if not r['id'].startswith('clearance_') else hashlib.sha256(('route-clearance-v14-'+r['id']).encode()).hexdigest()[:16];route_ids[r['id']]=rid
 pts=r['pointsMm'];path=[pts[0][0]/.0254,pts[0][1]/.0254,'L']+[v/.0254 for p in pts[1:] for v in p]
 q={'partitionId':'','groupId':0,'netName':r['net'],'layerId':r['layer'],'width':r['widthMm']/.0254,'path':path,'locked':False,'zIndex':-1,'polyType':'NORMAL'}
 edits[('PCB',pcb,'POLY',rid)]=q
for v in plan['vias']:
 vid=v['id'] if not v['id'].startswith('clearance_') else hashlib.sha256(('via-clearance-v14-'+v['id']).encode()).hexdigest()[:16];via_ids[v['id']]=vid
 q=copy.deepcopy(a.get(('PCB',pcb,'VIA',vid),{'partitionId':'','groupId':0,'locked':False,'zIndex':-1,'netName':v['net'],'ruleName':'','viaType':0,'unusedInnerLayers':[]}))
 q.update({'centerX':v['x']/.0254,'centerY':v['y']/.0254,'viaDiameter':v['diameter']/.0254,'holeDiameter':v['hole']/.0254})
 if vid not in [k[-1] for k in a if k[:3]==('PCB',pcb,'VIA')]:q.update({'topSolderExpansion':-v['diameter']/2/.0254,'bottomSolderExpansion':-v['diameter']/2/.0254})
 edits[('PCB',pcb,'VIA',vid)]=q
target=E/'DTU-V0.14-60x75-Clearancefix-routed-input.epro2';write_project(source,target,edits)
folder=str((R/'native-Clearancefix-final-v14').resolve());Path(folder).mkdir(exist_ok=True)
js="const f=new File([Uint8Array.from(atob("+json.dumps(base64.b64encode(target.read_bytes()).decode())+"),c=>c.charCodeAt(0))],'DTU-V0.14-60x75-Clearancefix.epro2');return {imported:await eda.sys_FileManager.importProjectByProjectFile(f,'JLCEDA Pro',{importOption:'ImportDocument',associateFootprint:true,associate3DModel:true,importFootprintNotesLayer:true},{operation:'Offline Client Local Path',folderPath:"+json.dumps(folder)+"})};"
(R/'scripts/import-clearancefix-final-v14.js').write_text(js,encoding='utf8')
(M/'clearancefix-native-id-map-v14.json').write_text(json.dumps({'routes':route_ids,'vias':via_ids},indent=2),encoding='utf8')
print('Prepared',len(plan['routes']),'routes',len(plan['vias']),'vias')
