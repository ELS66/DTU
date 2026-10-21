from pathlib import Path
import json
P=Path('PCB');p=P/'manifests/pcb-local-route-plan-v04.json';plan=json.loads(p.read_text());plan['routes']=[r for r in plan['routes']if not r['net'].startswith('VIN')];plan['phase']='Local feedback, bootstrap and low speed signals; all VIN, power distribution, RF and USB pending';p.write_text(json.dumps(plan,indent=2));guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");'
for i in range(0,len(plan['routes']),12):
 specs=[]
 for r in plan['routes'][i:i+12]:
  pts=r['pointsMm'];poly=[pts[0][0]/.0254,pts[0][1]/.0254,'L'];poly.extend(v/.0254 for pt in pts[1:]for v in pt);specs.append({'net':r['net'],'width':r['widthMm']/.0254,'poly':poly})
 code=guard+'const Layer={TOP:1};const specs='+json.dumps(specs)+';const out=[];for(const z of specs){const polygon=eda.pcb_MathPolygon.createPolygon(z.poly);const p=await eda.pcb_PrimitivePolyline.create(z.net,Layer.TOP,polygon,z.width,true);if(!p)throw Error("Route failed "+z.net);out.push({net:z.net,id:p.getState_PrimitiveId()});}return {created:out,saved:await eda.pcb_Document.save()};';(P/f'scripts/route-local-v04-{i//12+1}.js').write_text(code)
print('local routes',len(plan['routes']))
