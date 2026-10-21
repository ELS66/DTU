"""Back up release; move only four stale inner-copper keepouts to existing top holes."""
from pathlib import Path
import json,datetime,shutil,math,hashlib
R=Path('PCB');M=R/'manifests';E=R/'eda'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
s=(R/'scripts/package-silkclean-v13.py').read_text(encoding='utf8');exec(s[s.index('def rows('):s.index('before=rows(')])
current=load(M/'current-pcb-delivery.json');old=rows(load(M/current['actualSourceSnapshot'])['result']['source']);live=rows(load(M/'mounts-audit-live-source-v14.json')['result']['source'])
assert old==live,'Current live PCB differs from delivered baseline'
backup=R/'backups'/('20261016-before-mount-keepout-fix-'+datetime.datetime.now().strftime('%H%M%S'));backup.mkdir()
for p in [Path(current[k]) for k in ['nativeProject','productionGerber','deliveryArchive']]+[M/'current-pcb-delivery.json',M/'mounts-audit-live-source-v14.json']:
 shutil.copy2(p,backup/p.name)
changes=[];regions=[]
for (t,i),q in live.items():
 if t!='REGION' or q['layerId'] not in [15,16]:continue
 vals=[v*.0254 for v in q['path'][0] if isinstance(v,(int,float))];xs,ys=vals[::2],vals[1::2];cx=(min(xs)+max(xs))/2;cy=(min(ys)+max(ys))/2
 regions.append({'id':i,'layer':q['layerId'],'centerMm':[cx,cy]})
 if abs(cy-66)>.001:continue
 assert min(abs(cx-4),abs(cx-56))<.001 and q['prohibitType']==['COPPER']
 new=[];coordinate=0
 for v in q['path'][0]:
  if isinstance(v,(int,float)):
   new.append(v+(5/.0254 if coordinate%2 else 0));coordinate+=1
  else:new.append(v)
 changes.append({'id':i,'layer':q['layerId'],'fromCenterMm':[cx,cy],'toCenterMm':[cx,cy+5],'oldPath':q['path'][0],'newPath':new})
assert len(changes)==4 and len(regions)==8
guard=(R/'scripts/read-clearancefix-source-v14.js').read_text(encoding='utf8').split('return {source:')[0]
js=guard+'const changes='+json.dumps(changes)+";for(const q of changes){const r=await eda.pcb_PrimitiveRegion.get(q.id);if(!r)throw Error('Mount keepout missing '+q.id);}for(const q of changes){const complexPolygon=eda.pcb_MathPolygon.createPolygon(q.newPath);if(!await eda.pcb_PrimitiveRegion.modify(q.id,{complexPolygon}))throw Error('Mount keepout move failed '+q.id);}return {updated:changes.map(q=>({id:q.id,layer:q.layer,center:q.toCenterMm})),saved:await eda.pcb_Document.save()};"
(R/'scripts/apply-mountfix-v14_1.js').write_text(js,encoding='utf8')
report={'revision':'V0.14.1','backupDirectory':str(backup.resolve()),'baseline':current,'regionMoves':changes,'holesUnchanged':True}
(M/'mountfix-plan-v14_1.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
for kind in ['project','gerber']:
 p=R/f'scripts/export-clearancefix-{kind}-v14.js';s=p.read_text(encoding='utf8').replace('DTU-V0.14-60x75-Clearancefix','DTU-V0.14.1-60x75-Mountfix')
 (R/f'scripts/export-mountfix-{kind}-v14_1.js').write_text(s,encoding='utf8')
print('Backup',backup,'four keepouts prepared')
