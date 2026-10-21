from pathlib import Path
import json
P=Path('PCB');m=json.loads((P/'manifests/design.json').read_text(encoding='utf-8'));n=json.loads((P/'reports/full-schematic-v04.net').read_text(encoding='utf-8'));byref={z['ref']:z for z in m['parts']};cs=sorted(n['components'].values(),key=lambda c:(byref.get(c['props']['Designator'],{}).get('page',2 if c['props']['Designator']=='U1'else 3),c['props']['Designator']));js=[]
for i,c in enumerate(cs):
 p=c['props'];ref=p['Designator'];x=2600+(i%16)*250;y=250+(i//16)*250
 z={'ref':ref,'device':{'libraryUuid':m['projectUuid'],'uuid':p['Device']},'x':x,'y':y,'props':{'designator':ref,'uniqueId':p['Unique ID'],'name':p.get('Name'),'manufacturer':p.get('Manufacturer'),'manufacturerId':p.get('Manufacturer Part'),'supplier':p.get('Supplier'),'supplierId':p.get('Supplier Part'),'addIntoBom':p.get('Add into BOM')=='yes','otherProperty':{k:v for k,v in p.items()if k in ['Value','Voltage Rating','Tolerance','Temperature Coefficient','Datasheet','Description','3D Model','3D Model Title','3D Model Transform']}}};js.append(z)
(P/'manifests/pcb-transfer-plan-v04.json').write_text(json.dumps(js,ensure_ascii=False,indent=2),encoding='utf-8')
guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=='+json.dumps(m['pcbUuid'])+')throw Error("Wrong PCB");'
for start in range(0,len(js),7):
 arr=js[start:start+7];code=guard+'const Layer={TOP:1};const specs='+json.dumps(arr)+';const old=await eda.pcb_PrimitiveComponent.getAll();const out=[];for(const z of specs){if(old.some(c=>c.getState_Designator()===z.ref))continue;const c=await eda.pcb_PrimitiveComponent.create(z.device,Layer.TOP,z.x,z.y,0,false);if(!c)throw Error("Create failed "+z.ref);await eda.pcb_PrimitiveComponent.modify(c,z.props);out.push({ref:z.ref,id:c.getState_PrimitiveId()});}return {created:out,saved:await eda.pcb_Document.save()};';(P/f'scripts/transfer-pcb-v04-{start//7+1}.js').write_text(code,encoding='utf-8')
print(len(js),'components;',len(list(range(0,len(js),7))),'batches')
