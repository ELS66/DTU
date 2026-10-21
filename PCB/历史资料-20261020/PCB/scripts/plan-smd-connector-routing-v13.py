from pathlib import Path
exec(Path('PCB/scripts/router-v13.py').read_text(encoding='utf8'))
base=json.load(open(P/'manifests/connected-routing-v13.json',encoding='utf8'))
changed={'J1','J2','J3','D6','R32','R100'}
removed=set();removedvias=set();affected=set()
oldpos={'D6':(32,9.5),'R32':(28.25,10),'R100':(37.5,9.5)}
oldpads=[]
for p in pads:
 if p['ref'] in oldpos:
  c=by[p['ref']];dx=oldpos[p['ref']][0]-c['x']*.0254;dy=oldpos[p['ref']][1]-c['y']*.0254;oldpads.append({**p,'geom':translate(p['geom'],dx,dy)})
 if p['ref'] in ['J1','J2','J3'] and int(p['number'])<5:oldpads.append({**p,'geom':Point(p['x'],3.3).buffer(.8)})
for i,r in enumerate(base['routes']):
 g=LineString(r['pointsMm']).buffer(r['widthMm']/2)
 if any(p['net']==r['net'] and p['net'] and g.intersects(p['geom'].buffer(.01)) and (p['layer']==r['layer'] or p['ref'].startswith('J')) for p in oldpads) or any(p['ref'] in changed and p['net']!=r['net'] and p['layer'] in [12,r['layer']] and g.distance(p['geom'])<.153 for p in pads):removed.add(i);affected.add(r['net'])
for i,v in enumerate(base['vias']):
 g=Point(v['x'],v['y']).buffer(v['diameter']/2)
 if any(p['ref'] in changed and p['net']!=v['net'] and g.distance(p['geom'])<.153 for p in pads):removedvias.add(i);affected.add(v['net'])
kept=[r for i,r in enumerate(base['routes']) if i not in removed];keptvias=[v for i,v in enumerate(base['vias']) if i not in removedvias]
for r in kept:tracks.append({'net':r['net'],'layer':r['layer'],'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2),'points':r['pointsMm']})
vias+=keptvias
exec('def groups(net):'+Path('PCB/scripts/plan-remaining-routing-v13.py').read_text(encoding='utf8').split('def groups(net):')[1].split('power={')[0])
print('ripup',len(removed),len(removedvias),'nets',sorted(affected),flush=True)
failed=[]
for p in [q for q in pads if q['ref'] in changed and q['net']]:
 src=(p['x'],p['y'],p['layer']);net=p['net'];affected.add(net)
 # New connector signal and power escapes are below their solder tails, under plastic housing.
 if p['ref'].startswith('J'):
  w=.6 if net=='VIN_IN' else .4 if net=='GND' else .2;dia=.65 if net in ['VIN_IN','GND'] else .45;hole=.3 if dia==.65 else .2
  dst=addvia(net,(p['x'],p['y']-2.4),dia,hole,src[:2],1,w)
  if dst and net in ['VIN_IN','GND']:addvia(net,(dst[0]+.9,dst[1]),dia,hole,dst,1,w)
 else:
  # Keep moved passives' fanouts short before reconnecting their existing networks.
  w=.2;dst=addvia(net,src[:2],.45,.2,src[:2],1,w)
 if not dst:failed.append({'fanout':p['ref']+':'+p['number']})
for net in sorted(affected-{'GND',''},key=lambda n:(n!='VIN_IN',n)):
 gs=groups(net);edges=0
 while len(gs)>1:
  choices=[]
  for i,a in enumerate(gs):
   for j in range(i):
    b=gs[j]
    for pa in a:
     pb=min(b,key=lambda z:math.dist(pa[:2],z[:2]));choices.append((math.dist(pa[:2],pb[:2]),i,j,pa,pb))
  success=False
  for dist,i,j,a,b in sorted(choices)[:15]:
   w=.6 if net.startswith('VIN') else .254 if net=='VDD_3V3' else .1524
   common=([1,2,16] if a[2]==12 else [a[2]]) if a[2]==b[2] or b[2]==12 else []
   if common and addline(net,common[0],[a[:2],b[:2]],w):success=True
   elif addroute(net,a,b,w,(1,2,16)):success=True
   if success:gs[j].extend(gs[i]);gs.pop(i);edges+=1;break
  if not success:failed.append({'net':net,'groups':len(gs),'representatives':[g[0] for g in gs]});break
 print(net,'edges',edges,'remaining',len(gs),flush=True)
summary={'removedRoutes':sorted(removed),'removedVias':sorted(removedvias),'addedRoutes':new.copy(),'addedVias':newvias.copy(),'failed':failed}
(P/'manifests/smd-routing-patch-v13.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
new[:]=kept+new;newvias[:]=keptvias+newvias
save_plan('smd-connected-routing-v13',failed)
