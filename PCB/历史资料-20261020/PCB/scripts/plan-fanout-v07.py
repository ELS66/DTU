import sys,json,math,heapq,collections,time
from pathlib import Path
sys.path.insert(0,str(Path('PCB/.tools').resolve()))
import numpy as np
import shapely
from shapely.geometry import Point,LineString,Polygon,box
from shapely.ops import unary_union
P=Path('PCB');cs=json.loads((P/'manifests/pcb-pads-power-v07.json').read_text(encoding='utf-8-sig'))['result'];old=json.loads((P/'manifests/routing-power-v07.json').read_text(encoding='utf-8-sig'))['result'];pads=[];tracks=[];vias=[];routes=[];fail=[]
for c in cs:
 for q in c['pads']:
  r={**q,'ref':c['ref'],'x':q['x']*.0254,'y':q['y']*.0254}
  if q['shape'][0]=='POLYGON':
   v=[x for x in q['shape'][1] if isinstance(x,(int,float))];pts=list(zip([x*.0254 for x in v[::2]],[x*.0254 for x in v[1::2]]));w=max(x[0] for x in pts)-min(x[0] for x in pts);h=max(x[1] for x in pts)-min(x[1] for x in pts)
  else:
   w,h=[x*.0254 for x in q['shape'][1:3]];ang=math.radians(q['rotation']);pts=[]
   for dx,dy in [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]:pts.append((r['x']+dx*math.cos(ang)-dy*math.sin(ang),r['y']+dx*math.sin(ang)+dy*math.cos(ang)))
  r['geom']=Polygon(pts);r['w']=w;r['h']=h;pads.append(r)
for t in old['lines']:tracks.append({'net':t['net'],'layer':t['layer'],'geom':LineString([(t['x1']*.0254,t['y1']*.0254),(t['x2']*.0254,t['y2']*.0254)]).buffer(t['width']*.0254/2)})
for t in old['polys']:
 if t['layer'] not in [1,2,15,16]:continue
 a=t['polygon'];pts=[(a[0]*.0254,a[1]*.0254)];v=[x for x in a[3:] if isinstance(x,(int,float))];pts +=list(zip([x*.0254 for x in v[::2]],[x*.0254 for x in v[1::2]]));tracks.append({'net':t['net'],'layer':t['layer'],'geom':LineString(pts).buffer(t['width']*.0254/2)})
for v in old['vias']:vias.append({'net':v['net'],'x':v['x']*.0254,'y':v['y']*.0254,'diameter':v['diameter']*.0254,'existing':True})
railnames={'GND','VIN_OR','VIN_PROT','VDD_3V3','VDD_4G','VDD_5V_IF','VIN_485','VIN_232','VIN_TTL','VIN_485_FUSED','VIN_232_FUSED','VIN_TTL_FUSED'}
obcache={}
def obstacles(net,layer):
 out=[q['geom'] for q in pads if q['net']!=net and (q['layer']==layer or q['layer']==12)]
 out+=[t['geom'] for t in tracks if t['net']!=net and t['layer']==layer]
 out+=[Point(v['x'],v['y']).buffer(v['diameter']/2) for v in vias if v['net']!=net]
 return unary_union(out)
for net in sorted(railnames,key=lambda n:(n!='GND',n)):
 obs=obstacles(net,1);viaobs=unary_union([obs]+[t['geom'] for t in tracks if t['net']!=net and t['layer']!=1]);allpads=unary_union([q['geom'] for q in pads]);count=0
 for q in [q for q in pads if q['net']==net and q['layer']==1]:
  source=(q['x'],q['y']);width=max(.1524,min(.4,min(q['w'],q['h'])*.8));chosen=[];need=2 if (net in ['VIN_OR','VIN_PROT','VDD_4G'] or (net=='VDD_3V3' and q['ref'] in ['U1','L2','C98','C99'])) else 1
  near=[v for v in vias if v['net']==net and math.dist(source,(v['x'],v['y']))<2.5]
  for v in sorted(near,key=lambda v:math.dist(source,(v['x'],v['y']))):
   line=LineString([source,(v['x'],v['y'])])
   if line.buffer(width/2+.17).intersects(obs):continue
   routes.append({'net':net,'layer':1,'widthMm':width,'pointsMm':[list(source),[v['x'],v['y']]]});chosen.append(v);break
  if chosen:continue
  cand=[]
  for d in [.65,.8,1.,1.2,1.5,1.8,2.1,2.5]:
   for i in range(16):
    a=i*math.pi/8;x=round((source[0]+d*math.cos(a))/.025)*.025;y=round((source[1]+d*math.sin(a))/.025)*.025;circle=Point(x,y).buffer(.3);line=LineString([source,(x,y)])
    if not(.75<x<59.25 and .75<y<69.25):continue
    if circle.buffer(.17).intersects(viaobs) or circle.intersects(allpads) or line.buffer(width/2+.17).intersects(obs):continue
    if any(Point(v['x'],v['y']).distance(circle)<.4 for v in vias):continue
    cand.append((math.dist(source,(x,y)),x,y))
  for _,x,y in sorted(cand):
   if any(math.dist((x,y),(v['x'],v['y']))<.75 for v in chosen):continue
   v={'net':net,'x':x,'y':y,'diameter':.6};vias.append(v);chosen.append(v);routes.append({'net':net,'layer':1,'widthMm':width,'pointsMm':[list(source),[x,y]]});count+=1
   if len(chosen)>=need:break
  if not chosen:fail.append({'stage':'fanout','net':net,'pad':q['ref']+':'+q['number']})
 tracks.extend({'net':r['net'],'layer':r['layer'],'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2)} for r in routes if r['net']==net)
 print('fanout',net,count,flush=True)
plan={'vias':[v for v in vias if not v.get('existing')],'routes':routes,'failed':fail};(P/'manifests/power-ground-fanout-v07.json').write_text(json.dumps(plan,indent=2));print('fanout summary',len(plan['vias']),len(routes),'failed',fail,flush=True)
guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");'
items=[{'kind':'via',**v} for v in plan['vias']]+[{'kind':'route',**r} for r in routes]
for i in range(0,len(items),30):
 specs=items[i:i+30];code=guard+'const specs='+json.dumps(specs)+';for(const z of specs){if(z.kind==="via"){if(!await eda.pcb_PrimitiveVia.create(z.net,z.x/.0254,z.y/.0254,.3/.0254,.6/.0254,0,undefined,undefined,false))throw Error("Via failed");}else{const p=z.pointsMm;const a=[p[0][0]/.0254,p[0][1]/.0254,"L",...p.slice(1).flatMap(q=>q.map(v=>v/.0254))];if(!await eda.pcb_PrimitivePolyline.create(z.net,z.layer,eda.pcb_MathPolygon.createPolygon(a),z.widthMm/.0254,false))throw Error("Route failed");}}return {count:specs.length,saved:await eda.pcb_Document.save()};';(P/f'scripts/apply-fanout-v07-{i//30+1}.js').write_text(code)


