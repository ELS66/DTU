from pathlib import Path
import json
P=Path('PCB');fresh=json.load(open(P/'manifests/pcb-source-reimported-final-v12.json',encoding='utf-8'))['result']['source'];good=json.load(open(P/'manifests/pcb-source-ground-final-large-v12.json',encoding='utf-8'))['result']['source'];phys=[]
for line in good.splitlines():
 if '||' not in line:continue
 h,b=line.split('||',1);h=json.loads(h);b=json.loads(b.rstrip('|'))
 if h['type']=='LAYER_PHYS':
  layer=json.loads(h['id'])[1];h['id']=layer;phys.append(json.dumps(h,separators=(',',':'))+'||'+json.dumps(b,separators=(',',':'))+'|')
out=[]
for line in fresh.splitlines():
 if '||' in line and json.loads(line.split('||')[0])['type']=='LAYER_PHYS':continue
 out.append(line)
source='\n'.join(out+phys)+'\n';guard=(P/'scripts/final-read-pcb-pads-v12.js').read_text().split('const out=')[0]
code=guard+'if(!await eda.sys_FileManager.setDocumentSource('+json.dumps(source)+"))throw Error('Stack update failed');return {saved:await eda.pcb_Document.save()};"
(P/'scripts/apply-persistent-stack-v12.js').write_text(code,encoding='utf-8');print('Stack records',len(phys))
