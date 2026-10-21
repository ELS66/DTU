import json
from pathlib import Path
p=Path('PCB');d=json.loads((p/'manifests/routing-interface-v11.json').read_text(encoding='utf-8-sig'))['result'];sel=[];nets=set()
for t in d['polys']:
 a=t['polygon'];v=[x for x in a if isinstance(x,(int,float))];xs=[x*.0254 for x in v[::2]];ys=[y*.0254 for y in v[1::2]]
 if t['net']=='232_C1P' or (t['net']=='GND' and t['layer']==1 and t['width']*.0254<.3 and any(24<x<30 and 7<y<16 for x,y in zip(xs,ys))):sel.append(t['id']);nets.add(t['net'])
print('delete',len(sel),nets)
code='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");const ids='+json.dumps(sel)+';if(ids.length&&!await eda.pcb_PrimitivePolyline.delete(ids))throw Error("Local reroute failed");return {ids,saved:await eda.pcb_Document.save()};';(p/'scripts/open-rs232-routing-v11.js').write_text(code)
