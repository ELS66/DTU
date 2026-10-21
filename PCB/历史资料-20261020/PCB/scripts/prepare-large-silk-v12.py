import json,math
from pathlib import Path
P=Path('PCB');a=[]
def text(x,y,s,size=.75):a.append({'x':x,'y':y,'text':s,'size':size})
for x,name,labels in [(20.4,'LTE USB',['G','D+','D-','5V','B']),(39.6,'ESP USB',['G','D+','D-','EN','B'])]:
 text(x,68.25,name,1)
 for i,s in enumerate(labels):text(x+(i-2)*2.54,63.65,s,.65)
for x,name,labels in [(15.24,'RS485',['P','A','B','G']),(30,'RS232',['P','T','R','G']),(44.76,'TTL 5V',['P','T','R','G'])]:
 text(x,7.0,name,1)
 for i,s in enumerate(labels):text(x+(i-1.5)*2,5.55,s,.65)
for x in [3.8,56.2]:
 for y,s in zip([54.2,49.3,44.4],['R','G','B']):text(x,y,s,.8)
text(44,33.6,'TX',.85);text(52,33.6,'RX',.85);text(40.5,36.15,'DTU V0.12',.9);text(13,41.0,'ML307R-DL',.8);text(10.8,66.9,'LTE ANT',.7)
guard=(P/'scripts/read-pcb-pads-v12.js').read_text().split('const out=')[0]
code=guard+'const labels='+json.dumps(a)+";const ids=[];for(const z of labels){const s=await eda.pcb_PrimitiveString.create(3,z.x/.0254,z.y/.0254,z.text,'default',z.size/.0254,.15/.0254,5,0,false,0,false,false);if(!s)throw Error('Silk failed');ids.push(s.getState_PrimitiveId());}"
regions=[]
for x,y in [(4,4),(56,4),(4,66),(56,66)]:
 pts=[[(x+3.4*math.cos(i*math.pi/32))/.0254,(y+3.4*math.sin(i*math.pi/32))/.0254] for i in range(65)]
 regions.append([*pts[0],'L',*[v for p in pts[1:] for v in p]])
code+='const regions='+json.dumps(regions)+";for(const p of regions){if(!await eda.pcb_PrimitiveRegion.create(12,eda.pcb_MathPolygon.createPolygon(p),[5,2,6,7],'M3 washer clearance',0,false))throw Error('Keepout failed');}return {labels:ids,saved:await eda.pcb_Document.save()};"
(P/'scripts/apply-large-silk-v12.js').write_text(code,encoding='utf8')
(P/'manifests/silk-large-v12.json').write_text(json.dumps(a,indent=2),encoding='utf8')
# Selectively visible layers provide a legible native PCB screenshot.
for side in ['top','bottom']:
 layers=[1,3,5,9,11,12,48,49] if side=='top' else [2,4,6,10,11,12,48,49]
 c=guard+'await eda.pcb_Layer.setLayerVisible('+json.dumps(layers)+",true);await eda.pcb_Layer.setLayerInvisible(57);const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();await eda.dmt_EditorControl.zoomToAllPrimitives(d.tabId);const f=await eda.dmt_EditorControl.getCurrentRenderedAreaImage(d.tabId);return {name:'DTU-V0.12-native-"+side+".png',bytes:Array.from(new Uint8Array(await f.arrayBuffer()))};"
 (P/f'scripts/capture-{side}-large-v12.js').write_text(c,encoding='utf8')
