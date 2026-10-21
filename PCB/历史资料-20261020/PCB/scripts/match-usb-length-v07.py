from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text().replace('pcb-pads-power-v07.json','pcb-pads-usb-v07.json').replace('routing-power-v07.json','routing-resume-v07.json'))
plan=json.loads((P/'manifests/usb-routing-plan-v07.json').read_text());oldtracks=list(tracks)
for v in plan['vias']:vias.append(v)
for r in plan['routes']:tracks.append({'net':r['net'],'layer':r['layer'],'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2)})
report=[]
for family in ['ESP','LTE']:
 def total(polarity):return sum(LineString(r['pointsMm']).length for r in plan['routes'] if r['net'].startswith(family+'_USB_'+polarity) and r['role']!='ESD-to-header')
 a,b=total('DP'),total('DM');short='DM' if a>b else 'DP';delta=abs(a-b);candidates=[]
 for index,r in enumerate(plan['routes']):
  if not r['net'].startswith(family+'_USB_'+short) or r['role'] in ['ESD-to-header','coupled-core','coupled-input-core']:continue
  pts=r['pointsMm'];obs=obstacles(r['net'],r['layer'])
  for i,(u,v) in enumerate(zip(pts,pts[1:])):
   length=math.dist(u,v)
   if length<.2:continue
   h=.5*math.sqrt((length+delta)**2-length**2)
   for sign in [-1,1]:
    middle=[(u[0]+v[0])/2-sign*(v[1]-u[1])/length*h,(u[1]+v[1])/2+sign*(v[0]-u[0])/length*h];newpts=pts[:i+1]+[middle]+pts[i+1:];g=LineString(newpts)
    if not box(.35,.35,59.65,69.65).covers(g.buffer(r['widthMm']/2)):continue
    if g.buffer(r['widthMm']/2+.153).intersects(obs):continue
    # 防止新增绕线与本网络其他线路相交，形成实际导电捷径。
    own=[LineString(z['pointsMm']) for j,z in enumerate(plan['routes']) if j!=index and z['net']==r['net'] and z['layer']==r['layer']]
    ends=Point(*pts[0]).buffer(.42).union(Point(*pts[-1]).buffer(.42))
    if own and g.difference(ends).buffer(r['widthMm']/2).intersects(unary_union(own).difference(ends)):continue
    candidates.append((h,index,newpts))
 if not candidates:report.append({'family':family,'DPmm':a,'DMmm':b,'matched':False});continue
 _,index,points=min(candidates,key=lambda x:x[0]);plan['routes'][index]['pointsMm']=points;plan['routes'][index]['lengthMatched']=True;report.append({'family':family,'beforeDPmm':a,'beforeDMmm':b,'DPmm':total('DP'),'DMmm':total('DM'),'matched':True,'adjustedRole':plan['routes'][index]['role']})
(P/'reports/usb-length-match-v07.json').write_text(json.dumps(report,indent=2));print(report);(P/'manifests/usb-routing-plan-v07.json').write_text(json.dumps(plan,indent=2))
guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");';code=guard+'const plan='+json.dumps(plan)+';for(const v of plan.vias)if(!await eda.pcb_PrimitiveVia.create(v.net,v.x/.0254,v.y/.0254,.3/.0254,.6/.0254,0))throw Error("Via failed");for(const r of plan.routes){const p=r.pointsMm;const z=eda.pcb_MathPolygon.createPolygon([p[0][0]/.0254,p[0][1]/.0254,"L",...p.slice(1).flatMap(q=>q.map(x=>x/.0254))]);if(!await eda.pcb_PrimitivePolyline.create(r.net,r.layer,z,r.widthMm/.0254,false))throw Error("Route failed");}return {vias:plan.vias.length,routes:plan.routes.length,saved:await eda.pcb_Document.save()};';(P/'scripts/apply-usb-routing-v07.js').write_text(code)
