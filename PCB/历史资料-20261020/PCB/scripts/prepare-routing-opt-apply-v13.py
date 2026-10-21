from pathlib import Path
import json,hashlib
P=Path('PCB');before=json.loads((P/'manifests/routing-opt-baseline-v13.json').read_text());after=json.loads((P/'manifests/routing-optimized-v13.json').read_text())
validation=json.loads((P/'manifests/routing-optimization-check-v13.json').read_text())
assert not validation['conflicts'] and not validation['connectivityRegressions']
guard=(P/'scripts/read-pcb-source-v13.js').read_text().split('return {source:')[0]
rid={r['id'] for r in after['routes'] if 'id' in r};vid={v['id'] for v in after['vias'] if 'id' in v}
delrs=[r for r in before['routes'] if r['id'] not in rid];delvs=[v for v in before['vias'] if v['id'] not in vid]
newrs=[r for r in after['routes'] if 'id' not in r];newvs=[v for v in after['vias'] if 'id' not in v]
# Every protected primitive must be byte-for-byte unchanged in the candidate plan.
protected={'GND','VDD_3V3','VDD_4G','VIN_IN','VIN_DIODE','VIN_PROT','SIM_VDD','LTE_VDD_EXT','LTE_SW','LTE_BST','LTE_FB','MCU_LDO_FB','LTE_ANT','LTE_RF_FEED','232_VMINUS'}
for kind in ['routes','vias']:
 old=[r for r in before[kind] if r['net'] in protected or 'USB' in r['net'] or r['net'].startswith('232_C')]
 new=[r for r in after[kind] if r['net'] in protected or 'USB' in r['net'] or r['net'].startswith('232_C')]
 assert sorted(old,key=lambda z:z['id'])==sorted(new,key=lambda z:z['id'])
expected=[{'id':r['id'],'net':r['net'],'layer':r['layer']} for r in before['routes']]
code=guard+'const expected='+json.dumps(expected)+';const rs=await eda.pcb_PrimitivePolyline.getAll();const vs=await eda.pcb_PrimitiveVia.getAll();if(rs.length!==582||vs.length!==362||(await eda.pcb_PrimitiveComponent.getAll()).length!==104)throw Error("Baseline primitive count changed");for(const r of expected){const p=rs.find(p=>p.getState_PrimitiveId()===r.id);if(!p||p.getState_Net()!==r.net||p.getState_Layer()!==r.layer)throw Error("Baseline route changed "+r.id);}return {checkedRoutes:expected.length,vias:vs.length};'
(P/'scripts/guard-routing-opt-apply-v13.js').write_text(code,encoding='utf8')
code=guard+'const rids='+json.dumps([r['id'] for r in delrs])+';const vids='+json.dumps([v['id'] for v in delvs])+';for(const id of rids){if(!await eda.pcb_PrimitivePolyline.get(id))throw Error("Missing old route "+id);}for(const id of vids){if(!await eda.pcb_PrimitiveVia.get(id))throw Error("Missing old via "+id);}if(rids.length&&!await eda.pcb_PrimitivePolyline.delete(rids))throw Error("Trace deletion");if(vids.length&&!await eda.pcb_PrimitiveVia.delete(vids))throw Error("Via deletion");return {removedRoutes:rids.length,removedVias:vids.length,saved:await eda.pcb_Document.save()};'
(P/'scripts/remove-routing-opt-old-v13.js').write_text(code,encoding='utf8')
items=[{'kind':'via',**v} for v in newvs]+[{'kind':'route',**r} for r in newrs]
scripts=[]
for i in range(0,len(items),20):
 code=guard+'const items='+json.dumps(items[i:i+20])+";const out=[];for(const z of items){let p;if(z.kind==='via'){p=await eda.pcb_PrimitiveVia.create(z.net,z.x/.0254,z.y/.0254,z.hole/.0254,z.diameter/.0254,0,null,{topSolderMask:-z.diameter/2/.0254,bottomSolderMask:-z.diameter/2/.0254},false);}else{const a=z.pointsMm;p=await eda.pcb_PrimitivePolyline.create(z.net,z.layer,eda.pcb_MathPolygon.createPolygon([...a[0].map(v=>v/.0254),'L',...a.slice(1).flatMap(q=>q.map(v=>v/.0254))]),z.widthMm/.0254,false);}if(!p)throw Error('Primitive creation');out.push({id:p.getState_PrimitiveId(),net:z.net,kind:z.kind});}return {created:out,saved:await eda.pcb_Document.save()};"
 name=f'apply-routing-opt-v13-{i//20+1}.js';scripts.append(name);(P/'scripts'/name).write_text(code,encoding='utf8')
summary={'beforeVias':len(before['vias']),'afterVias':len(after['vias']),'removedRoutes':len(delrs),'removedVias':len(delvs),'createdRoutes':len(newrs),'createdVias':len(newvs),'afterRoutes':len(after['routes']),'scripts':scripts,'planSha256':hashlib.sha256((P/'manifests/routing-optimized-v13.json').read_bytes()).hexdigest()}
(P/'manifests/routing-opt-apply-plan-v13.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
