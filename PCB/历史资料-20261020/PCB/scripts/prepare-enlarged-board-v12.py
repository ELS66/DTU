from pathlib import Path
import json
p=Path('PCB');s=json.load(open(p/'manifests/pcb-before-enlarge-v12.json',encoding='utf8'))['result']['source'];cs=json.load(open(p/'manifests/pcb-pads-current-v12.json',encoding='utf8'))['result'];by={c['id']:c for c in cs};forced={
 'U2':(17.04,50.295,90),'J4':(12,30,-90),'J5':(10.8,63.5,180),'J6':(39.6,65.5,0),'J7':(20.4,65.5,0),
 'R15':(31.5,40.0,180),'R16':(31.5,41.27,180),'R60':(21.84,56.2,90),'R61':(20.64,56.2,90),
 'R50':(9.2,60.15,90),'C50':(7.5,60.15,90),'C51':(12.8,60.6,0),'D10':(13.3,62.5,0),
 'D30':(58.2,54.2,90),'D31':(58.2,49.3,90),'D32':(58.2,44.4,90),
 'D33':(1.8,54.2,90),'D34':(1.8,49.3,90),'D35':(1.8,44.4,90),
 'D36':(44.0,35.0,0),'D37':(52.0,35.0,0)}
out=[];moves=[]
for l in s.splitlines():
 h,b=l.split('||',1);a=json.loads(h);d=json.loads(b.rstrip('|')) if b.rstrip('|') else None
 if d is None:continue
 t=a['type']
 if t in ['VIA','FILL','LINE','STRING','REGION']:continue
 if t=='POLY':
  if d['layerId']!=11:continue
  d['path']=[0,0,'L',0,70/.0254,60/.0254,70/.0254,60/.0254,0,0,0]
 if t=='PAD':d['centerX']=(4 if d['centerX']*.0254<10 else 56)/.0254;d['centerY']=(4 if d['centerY']*.0254<10 else 66)/.0254
 if t=='COMPONENT':
  c=by[a['id']];ref=c['ref'];x=c['x']*.0254*1.2;y=c['y']*.0254*7/6;r=c['rotation']
  if ref in ['J1','J2','J3']:y=3.3
  if ref in ['C81','C82','C83','C84']:y+=6.078333333
  if ref in forced:x,y,r=forced[ref]
  d['x']=x/.0254;d['y']=y/.0254;d['angle']=r;moves.append({'ref':ref,'x':x,'y':y,'rotation':r,'layer':c['layer']})
 if t=='ACTIVE_LAYER':d['layerId']=1
 out.append(json.dumps(a,ensure_ascii=False)+'||'+json.dumps(d,ensure_ascii=False)+'|')
source='\n'.join(out)+'\n';(p/'manifests/enlarged-placement-v12.json').write_text(json.dumps(moves,indent=2),encoding='utf8')
g=(p/'scripts/read-pcb-pads-v12.js').read_text().split('const out=')[0]
(p/'scripts/enlarge-board-v12.js').write_text(g+'if(!await eda.sys_FileManager.setDocumentSource('+json.dumps(source,ensure_ascii=False)+'))throw Error("Enlarged layout failed");return {saved:await eda.pcb_Document.save(),components:(await eda.pcb_PrimitiveComponent.getAll()).length};',encoding='utf8')
r=json.load(open(p/'manifests/revision-v12.json',encoding='utf8'));r['requirements']['boardTargetMm']=[60,70];r['requirements']['moduleAlignment']='physical upper edges aligned';(p/'manifests/revision-v12.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8')
