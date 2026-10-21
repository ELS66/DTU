from pathlib import Path
import json
p=Path('PCB');plan=json.loads((p/'manifests/pcb-additions-layout-v06.json').read_text());a=[]
for r,label in [('D36','TX'),('D37','RX')]:
 z=plan['newPositions'][r];a.append({'x':z['xMm']/.0254,'y':68.8/.0254,'text':label})
code='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");const specs='+json.dumps(a)+';const all=await eda.pcb_PrimitiveString.getAll(3);for(const z of specs){let t=all.find(p=>p.getState_Text()===z.text);if(t)await eda.pcb_PrimitiveString.modify(t,{x:z.x,y:z.y});else if(!await eda.pcb_PrimitiveString.create(3,z.x,z.y,z.text,"default",28,4,5,0,false,0,false,false))throw Error("Label failed");}return {saved:await eda.pcb_Document.save()};';(p/'scripts/label-activity-v06.js').write_text(code)
