import json
from pathlib import Path
p=Path('PCB');n=json.loads((p/'reports/full-schematic-v05.net').read_text(encoding='utf-8'));plan=json.loads((p/'manifests/revision-v05.json').read_text(encoding='utf-8'));cs={c['props']['Designator']:c for c in n['components'].values()};replace=['U10','J6','J7'];new=['C110']+[r for z in plan['leds'] for r in [z['diode'],z['resistor']]]+replace
base='''if((await eda.dmt_Project.getCurrentProjectInfo())?.uuid!=="b7122aadd3e496b681150192bfbef370394a2ba91164cb1621df30a137bdfaf5")throw Error("Wrong project");await eda.dmt_EditorControl.openDocument("4211128ecf040c100b33238447713203");if(eda.sys_Storage.getExtensionUserConfig("DTU_V04_ROUTING_JOB_20261010")?.status==="running")throw Error("Routing running");'''
code=base+'const refs='+json.dumps(plan['removed']+replace)+''';const deleted=[];for(const c of await eda.pcb_PrimitiveComponent.getAll())if(refs.includes(c.getState_Designator())){if(!await eda.pcb_PrimitiveComponent.delete(c))throw Error("Delete failed");deleted.push(c.getState_Designator());}const stale=["Q4_BASE","LTE_NETSTATUS_N","TTL_VREF"];for(const p of await eda.pcb_PrimitiveLine.getAll())if(stale.includes(p.getState_Net()))await eda.pcb_PrimitiveLine.delete(p);for(const p of await eda.pcb_PrimitiveVia.getAll())if(stale.includes(p.getState_Net()))await eda.pcb_PrimitiveVia.delete(p);for(const p of await eda.pcb_PrimitivePolyline.getAll())if(stale.includes(p.getState_Net()))await eda.pcb_PrimitivePolyline.delete(p);return {deleted,saved:await eda.pcb_Document.save()};'''
(p/'scripts/sync-pcb-remove-v05.js').write_text(code,encoding='utf-8')
core=['Unique ID','Designator','Name','Manufacturer','Manufacturer Part','Supplier','Supplier Part','Add into BOM','Convert to PCB','Device','Footprint','PCB Layer','Symbol']
for batch in range(4):
 specs=[]
 for i,r in enumerate(new[batch*5:(batch+1)*5]):
  a=cs[r]['props'];props={'designator':r,'uniqueId':a['Unique ID'],'name':a.get('Name',''),'manufacturer':a.get('Manufacturer',''),'manufacturerId':a.get('Manufacturer Part',''),'supplier':a.get('Supplier',''),'supplierId':a.get('Supplier Part',''),'addIntoBom':r not in plan['dnp'],'otherProperty':{k:v for k,v in a.items() if k not in core}}
  specs.append({'ref':r,'device':{'libraryUuid':n['projectId'],'uuid':a['Device']},'x':2800+i*200,'y':500+batch*400,'props':props})
 code=base+'const Layer={TOP:1};const specs='+json.dumps(specs,ensure_ascii=False)+''';const done=[];for(const z of specs){let c=(await eda.pcb_PrimitiveComponent.getAll()).find(c=>c.getState_Designator()===z.ref);if(!c){c=await eda.pcb_PrimitiveComponent.create(z.device,Layer.TOP,z.x,z.y,0,false);if(!c)throw Error("Create failed "+z.ref);await eda.pcb_PrimitiveComponent.modify(c,z.props);}done.push(z.ref);}return {created:done,saved:await eda.pcb_Document.save()};'''
 (p/f'scripts/sync-pcb-add-v05-{batch+1}.js').write_text(code,encoding='utf-8')
for batch in range(12):
 refs=list(cs)[batch*15:(batch+1)*15];sub={r:plan['expected'][r] for r in refs};props=[]
 for r in refs:
  a=cs[r]['props'];props.append({'ref':r,'otherProperty':{k:v for k,v in a.items() if k not in core},'addIntoBom':r not in plan['dnp']})
 code=base+'const map='+json.dumps(sub)+';const specs='+json.dumps(props,ensure_ascii=False)+''';const changed=[];const missing=[];for(const c of await eda.pcb_PrimitiveComponent.getAll()){const ref=c.getState_Designator();if(!map[ref])continue;const spec=specs.find(z=>z.ref===ref);await eda.pcb_PrimitiveComponent.modify(c,{otherProperty:spec.otherProperty,addIntoBom:spec.addIntoBom});const pins=await eda.pcb_PrimitiveComponent.getAllPinsByPrimitiveId(c.getState_PrimitiveId());const nums=new Set(pins.map(p=>p.getState_PadNumber()));for(const num of Object.keys(map[ref]))if(!nums.has(num))missing.push(ref+":"+num);for(const pin of pins){const net=map[ref][pin.getState_PadNumber()]||"";if(pin.getState_Net()!==net){const a=pin.toAsync();a.setState_Net(net);await a.done();changed.push(ref+":"+pin.getState_PadNumber());}}}return {changed,missing,saved:await eda.pcb_Document.save()};'''
 (p/f'scripts/sync-pcb-nets-v05-{batch+1}.js').write_text(code,encoding='utf-8')
print('PCB revision scripts generated for 180 components')
