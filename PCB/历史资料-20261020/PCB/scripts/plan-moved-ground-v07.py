from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text(encoding='utf-8').replace('pcb-pads-power-v07.json','pcb-pads-usb-v07.json').replace('routing-power-v07.json','routing-post-usb-v07.json'))
newvia=[];newroute=[];failed=[]
for ref in ['R14','C100','C102','D18','D19','D20','D21']:
 num=next(p['number'] for p in pads if p['ref']==ref and p['net']=='GND')
 q=next(q for q in pads if q['ref']==ref and q['number']==num);source=(q['x'],q['y']);width=.1524;obs=obstacles('GND',1);viaobs=unary_union([obs]+[t['geom'] for t in tracks if t['net']!='GND' and t['layer']!=1]);allpads=unary_union([q['geom'] for q in pads]);candidates=[]
 for v in vias:
  if v['net']!='GND' or math.dist(source,(v['x'],v['y']))>3:continue
  line=LineString([source,(v['x'],v['y'])])
  if not line.buffer(width/2+.16).intersects(obs):candidates.append((math.dist(source,(v['x'],v['y'])),v['x'],v['y'],True))
 for d in [.65,.8,1.,1.2,1.5,1.8,2.1,2.5,3.]:
  for i in range(32):
   x=round((source[0]+d*math.cos(i*math.pi/16))/.025)*.025;y=round((source[1]+d*math.sin(i*math.pi/16))/.025)*.025;c=Point(x,y).buffer(.3);line=LineString([source,(x,y)])
   if c.buffer(.17).intersects(viaobs) or c.intersects(allpads) or line.buffer(width/2+.16).intersects(obs):continue
   if any(math.dist((x,y),(v['x'],v['y']))<.8 for v in vias):continue
   candidates.append((d,x,y,False))
 if not candidates:failed.append(ref+':'+num);continue
 _,x,y,existing=min(candidates)
 if not existing:newvia.append({'net':'GND','x':x,'y':y});vias.append({'net':'GND','x':x,'y':y,'diameter':.6})
 newroute.append({'net':'GND','layer':1,'widthMm':width,'pointsMm':[list(source),[x,y]]});print(ref,num,'groundVia',x,y,'existing',existing)
plan={'vias':newvia,'routes':newroute,'failed':failed};(P/'manifests/moved-ground-repair-v07.json').write_text(json.dumps(plan,indent=2));print('failed',failed)
code='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");const vias='+json.dumps(newvia)+';const routes='+json.dumps(newroute)+';for(const v of vias)if(!await eda.pcb_PrimitiveVia.create(v.net,v.x/.0254,v.y/.0254,.3/.0254,.6/.0254,0))throw Error("Via failed");for(const z of routes){const p=z.pointsMm;const poly=eda.pcb_MathPolygon.createPolygon([p[0][0]/.0254,p[0][1]/.0254,"L",p[1][0]/.0254,p[1][1]/.0254]);if(!await eda.pcb_PrimitivePolyline.create(z.net,z.layer,poly,z.widthMm/.0254,false))throw Error("Route failed");}return {saved:await eda.pcb_Document.save()};';(P/'scripts/apply-moved-ground-repair-v07.js').write_text(code)
