"""Compile a fresh V0.12 PCB base from verified source and schematic export."""
import json
from pathlib import Path
P=Path('PCB');project='be907e0c26ece4ccdedd2f5b24e25f76812bc6b957961675838d5450e3220cbc';pcb='4211128ecf040c100b33238447713203'
def js(v):return json.dumps(v,ensure_ascii=False)
def read(n):return json.loads((P/n).read_text(encoding='utf-8-sig'))
guard=f"if((await eda.dmt_Project.getCurrentProjectInfo())?.uuid!=={js(project)}||(await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=={js(pcb)})throw Error('Wrong V0.12 PCB');"
source=read('manifests/pcb-source-before-v12.json')['result']['source']
retain={'DOCHEAD','CANVAS','LAYER','LAYER_PHYS','ACTIVE_LAYER','COMPONENT','PAD_NET','ATTR','NET','RULE_SELECTOR','RULE','RULE_TEMPLATE','PRIMITIVE','SILK_OPTS','PREFERENCE','D3_ATTRIBUTE','PANELIZE'}
clean='\n'.join(line for line in source.splitlines() if json.loads(line.split('||')[0])['type'] in retain)+'\n'
(P/'scripts/clear-pcb-layout-v12.js').write_text(guard+'if(!await eda.sys_FileManager.setDocumentSource('+js(clean)+"))throw Error('Source replacement failed');return {saved:await eda.pcb_Document.save()};",encoding='utf-8')
n=json.loads(read('manifests/schematic-after-v12.json')['result']['content']);parts={c['props']['Designator']:c for c in n['components'].values()};plan=read('manifests/revision-v12.json');old=read('manifests/pcb-pads-before-layout-v12.json')['result'];omap={c['ref']:c for c in old}
replaced=['U2','U4','U10','L1','R55','R64'];remove=plan['removedThisRevision']+replaced
create=[r for r in parts if r not in omap or r in replaced]
specs=[]
for i,r in enumerate(create):
    a=parts[r]['props'];s={'ref':r,'device':{'libraryUuid':project,'uuid':a['Device']},'props':{'designator':r,'uniqueId':a['Unique ID'],'name':a['Name'],'manufacturer':a.get('Manufacturer',''),'manufacturerId':a.get('Manufacturer Part',''),'supplier':a.get('Supplier',''),'supplierId':a.get('Supplier Part',''),'addIntoBom':r not in plan['dnp'],'otherProperty':{k:v for k,v in a.items() if k not in ['Unique ID','Name','Designator','Manufacturer','Manufacturer Part','Supplier','Supplier Part','Add into BOM','Convert to PCB']}}}
    specs.append(s)
code=guard+'const refs='+js(remove)+";const cs=await eda.pcb_PrimitiveComponent.getAll();const ids=cs.filter(c=>refs.includes(c.getState_Designator())).map(c=>c.getState_PrimitiveId());if(ids.length&&!await eda.pcb_PrimitiveComponent.delete(ids))throw Error('Delete failed');"
code+='const specs='+js(specs)+";for(let i=0;i<specs.length;i++){const s=specs[i];const c=await eda.pcb_PrimitiveComponent.create(s.device,1,(55+i*4)/.0254,30/.0254,0,false);if(!c)throw Error('Create failed '+s.ref);if(!await eda.pcb_PrimitiveComponent.modify(c,s.props))throw Error('Properties failed '+s.ref);}return {created:specs.length,saved:await eda.pcb_Document.save()};"
(P/'scripts/replace-pcb-components-v12.js').write_text(code,encoding='utf-8')
metadata={r:{'uniqueId':c['props']['Unique ID'],'otherProperty':{'Channel ID':c['props'].get('Channel ID','')}} for r,c in parts.items()}
code=guard+'const map='+js(plan['expected'])+';const metadata='+js(metadata)+';const netlist='+js(js(n))+";if(!await eda.pcb_Net.setNetlist('EasyEDA',netlist))throw Error('Netlist update failed');for(const c of await eda.pcb_PrimitiveComponent.getAll()){const r=c.getState_Designator();if(!map[r])throw Error('Unexpected '+r);if(!await eda.pcb_PrimitiveComponent.modify(c,metadata[r]))throw Error('Identity sync failed');for(const p of await eda.pcb_PrimitiveComponent.getAllPinsByPrimitiveId(c.getState_PrimitiveId())){const net=map[r][p.getState_PadNumber()]||'';if(p.getState_Net()!==net){const a=p.toAsync();a.setState_Net(net);await a.done();}}}return {saved:await eda.pcb_Document.save(),components:(await eda.pcb_PrimitiveComponent.getAll()).length};"
(P/'scripts/sync-pcb-nets-v12.js').write_text(code,encoding='utf-8')
print('PCB fresh source:',len(clean),'created:',create)
