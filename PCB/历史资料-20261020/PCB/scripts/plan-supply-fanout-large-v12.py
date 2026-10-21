from pathlib import Path
exec(Path('PCB/scripts/router-large-v12.py').read_text(encoding='utf-8'))
for name in ['critical-large-v12']:load_plan(P/f'manifests/{name}.json')
power=['VIN_485','VIN_232','VIN_TTL','VIN_485_FUSED','VIN_232_FUSED','VIN_TTL_FUSED','VIN_OR','VIN_PROT','VDD_4G','VDD_3V3','VDD_5V_IF','LTE_VDD_EXT','SIM_VDD']
failed=[];done=[]
for net in ['GND']+power:
 obsall=unary_union([obstacles(net,k) for k in layers]);own=unary_union([p['geom'] for p in pads if p['net']==net])
 for q in [q for q in pads if q['net']==net and q['layer']!=12]:
  source=(q['x'],q['y']);width=.4 if net=='VDD_4G' or (net.startswith('VIN') and q['ref'][0] in 'CDFQ') else .254
  obs=obstacles(net,q['layer']);options=[]
  for v in vias:
   if v['net']==net and math.dist(source,(v['x'],v['y']))<3 and LineString([source,(v['x'],v['y'])]).distance(obs)>=width/2+.153:options.append((math.dist(source,(v['x'],v['y'])),v['x'],v['y'],True))
  thermal=net=='GND' and ((q['ref']=='U1' and q['number']=='29') or (q['ref']=='U2' and q['number'] in [str(n) for n in range(88,95)]))
  dia=.6 if net.startswith('VIN') or net in ['VDD_4G','VDD_3V3','VDD_5V_IF'] else .45
  for d in [0,.5,.65,.8,1,1.2,1.5,1.8,2.2,2.8,3.5,4.2]:
   if options and d>min(options)[0]+.05:break
   for i in range(32):
    x=round((source[0]+d*math.cos(i*math.pi/16))/.025)*.025;y=round((source[1]+d*math.sin(i*math.pi/16))/.025)*.025;pt=Point(x,y)
    if not .65<x<59.35 or not .65<y<69.35 or pt.distance(obsall)<dia/2+.158:continue
    if not thermal and pt.distance(own)<dia/2+.04:continue
    if any(math.dist((x,y),(v['x'],v['y']))<(dia+v['diameter'])/2+.158 for v in vias):continue
    if LineString([source,(x,y)]).distance(obs)<width/2+.153:continue
    options.append((d,x,y,False))
  if not options:
   failed.append({'net':net,'ref':q['ref'],'pin':q['number'],'point':source,'layer':q['layer']});continue
  d,x,y,existing=min(options)
  if not existing:
   v={'net':net,'x':x,'y':y,'diameter':dia,'hole':.3 if dia==.6 else .2};vias.append(v);newvias.append(v)
  if math.dist(source,(x,y))>.0001:assert addline(net,q['layer'],[source,(x,y)],width)
  done.append({'net':net,'ref':q['ref'],'pin':q['number'],'via':[x,y]})
 print(net,'connected',sum(x['net']==net for x in done),'failed',sum(x['net']==net for x in failed),flush=True)
save_plan('supply-ground-fanout-large-v12',failed)
(P/'manifests/fanout-connected-large-v12.json').write_text(json.dumps(done,indent=2))
