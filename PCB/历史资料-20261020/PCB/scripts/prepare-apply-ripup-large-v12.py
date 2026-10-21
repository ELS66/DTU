import json
from pathlib import Path
P=Path('PCB');r=json.load(open(P/'manifests/escape-ripup-large-v12.json'))['removed'];guard=(P/'scripts/read-pcb-pads-v12.js').read_text().split('const out=')[0]
code=guard+'const wanted='+json.dumps(r)+";const all=await eda.pcb_PrimitivePolyline.getAll();for(const [id,net] of Object.entries(wanted)){const p=all.find(x=>x.getState_PrimitiveId()===id);if(!p||p.getState_Net()!==net)throw Error('Rip-up state changed '+id);}return {deleted:await eda.pcb_PrimitivePolyline.delete(Object.keys(wanted)),saved:await eda.pcb_Document.save()};"
(P/'scripts/apply-selective-ripup-large-v12.js').write_text(code,encoding='utf-8')
