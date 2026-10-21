import json
from pathlib import Path
P=Path('PCB');n=json.loads((P/'reports/full-schematic-v04.net').read_text(encoding='utf-8'));cs=json.loads((P/'manifests/pcb-layout-pads-v04.json').read_text(encoding='utf-8-sig'))['result'];by={c['ref']:c for c in cs};err=[];pins=0
for c in n['components'].values():
 r=c['props']['Designator'];pmap={p['number']:p['net']for p in by[r]['pads']}
 for pn,p in c['pinInfoMap'].items():
  pins+=1
  if pmap.get(pn,'')!=p.get('net',''):err.append([r,pn,p.get('net'),pmap.get(pn)])
print('all Schematic Pins',pins,'differences',err)
exclude={'Device','Symbol','Footprint','Unique ID','Designator','Name','Manufacturer','Manufacturer Part','Supplier','Supplier Part','Add into BOM','Convert to PCB','PCB Layer','DeviceName','FootprintName'};specs=[]
for c in n['components'].values():
 p=c['props'];specs.append({'ref':p['Designator'],'props':{'manufacturer':p.get('Manufacturer',''),'manufacturerId':p.get('Manufacturer Part',''),'supplier':p.get('Supplier',''),'supplierId':p.get('Supplier Part',''),'otherProperty':{k:v for k,v in p.items()if k not in exclude}}})
guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");'
for i in range(0,len(specs),20):
 code=guard+'const specs='+json.dumps(specs[i:i+20],ensure_ascii=False)+';const cs=await eda.pcb_PrimitiveComponent.getAll();for(const z of specs){const c=cs.find(c=>c.getState_Designator()===z.ref);if(!c)throw Error(z.ref);await eda.pcb_PrimitiveComponent.modify(c,z.props);}return {updated:specs.length,saved:await eda.pcb_Document.save()};'
 (P/f'scripts/restore-pcb-properties-v04-{i//20+1}.js').write_text(code,encoding='utf-8')
