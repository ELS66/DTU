from pathlib import Path
import json,collections
P=Path('PCB');w=json.loads((P/'reports/pcb-view-wrapper-v04.json').read_text(encoding='utf-8-sig'));(P/'reports/PCB-V0.4-layout.png').write_bytes(bytes(w['result']['bytes']))
d=json.loads((P/'reports/pcb-drc-layout-v04.json').read_text(encoding='utf-8-sig'))['result']
def leaves(x):
 if isinstance(x,list):
  for y in x:yield from leaves(y)
 elif isinstance(x,dict):
  if 'list'in x:yield from leaves(x['list'])
  else:yield x
ls=list(leaves(d));print('DRC counts',collections.Counter(x.get('errorType',x.get('name'))for x in ls))
for x in ls:
 if x.get('errorType')!='Connection Error':print(str(x)[:1500])
n=json.loads((P/'reports/full-schematic-v04.net').read_text(encoding='utf-8'));specs=[{'ref':c['props']['Designator'],'props':{k:c['props'].get(k,'')for k in ['Channel ID','Group ID','Reuse Block']}}for c in n['components'].values()];guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");'
for i in range(0,len(specs),25):
 code=guard+'const specs='+json.dumps(specs[i:i+25])+';const cs=await eda.pcb_PrimitiveComponent.getAll();for(const z of specs){const c=cs.find(c=>c.getState_Designator()===z.ref);if(!c)throw Error(z.ref);await eda.pcb_PrimitiveComponent.modify(c,{otherProperty:z.props});}return {updated:specs.length,saved:await eda.pcb_Document.save()};'
 (P/f'scripts/sync-pcb-association-v04-{i//25+1}.js').write_text(code)
