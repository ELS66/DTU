from pathlib import Path
exec(Path('PCB/scripts/router-v13.py').read_text(encoding='utf-8'))
layers[:]=[1,2,16]
base=[]
for name in ['critical-routing-v13','interface-routing-v13','remaining-routing-v13','ground-fanout-v13']:
 a=json.load(open(P/f'manifests/{name}.json',encoding='utf-8'))
 for r in a['routes']:
  base.append(r);tracks.append({'net':r['net'],'layer':r['layer'],'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2),'points':r['pointsMm'],'source':len(base)-1,'protected':name in ['critical-routing-v13','interface-routing-v13']})
 vias.extend(a['vias'])
exec('def groups(net):'+Path('PCB/scripts/plan-remaining-routing-v13.py').read_text(encoding='utf-8').split('def groups(net):')[1].split('power={')[0])
removed=set();escapes=[];noescape=[]
protectednets={'LTE_ANT','LTE_RF_FEED'}|{f'{a}_USB_{b}{c}' for a in ['ESP','LTE'] for b in ['DP','DM'] for c in ['','_EXT']}
allnets=sorted({p['net'] for p in pads if p['net'] and p['net'] not in protectednets},key=lambda n:(n!='GND',n))
for net in allnets:
 gs=groups(net)
 if len(gs)<2:continue
 for group in gs:
  if any(a[2]==12 or any(v['net']==net and math.dist(a[:2],(v['x'],v['y']))<.01 for v in vias) for a in group):continue
  pp=[p for p in pads if p['net']==net and any(math.dist(a[:2],(p['x'],p['y']))<.01 and a[2]==p['layer'] for a in group)]
  if not pp:continue
  padobs=unary_union([p['geom'] for p in pads if p['net']!=net]+holes+[Point(v['x'],v['y']).buffer(v['diameter']/2) for v in vias]);own=unary_union([p['geom'] for p in pads if p['net']==net]);choices=[]
  for p in pp:
   surface=unary_union([q['geom'] for q in pads if q['net']!=net and q['layer'] in [12,p['layer']]]+holes+[Point(v['x'],v['y']).buffer(v['diameter']/2) for v in vias if v['net']!=net])
   for radius in [.6,.8,1,1.2,1.5,1.8,2.2,2.8,3.5,4.5]:
    for k in range(32):
     x=round((p['x']+radius*math.cos(k*math.pi/16))/.05)*.05;y=round((p['y']+radius*math.sin(k*math.pi/16))/.05)*.05;pt=Point(x,y)
     if not(.75<x<59.25 and .75<y<69.25) or pt.distance(padobs)<.225+.16 or pt.distance(own)<.225+.04:continue
     dx=x-p['x'];dy=y-p['y'];diag=min(abs(dx),abs(dy));mid=(p['x']+math.copysign(diag,dx),p['y']+math.copysign(diag,dy));points=[(p['x'],p['y']),mid,(x,y)];line=LineString(points)
     if line.distance(surface)<.0762+.153:continue
     blockers=[t for t in tracks if t['net']!=net and ((t['layer']==p['layer'] and line.distance(t['geom'])<.0762+.16) or pt.distance(t['geom'])<.225+.16)]
     if any(t.get('protected') or 'source' not in t for t in blockers) or len(blockers)>3:continue
     choices.append((len(blockers)*100+radius,p['ref'],p['number'],x,y,points,blockers,p['layer']))
   if choices and min(c[0] for c in choices)<1.51:break
  if not choices:noescape.append([net,[p['ref']+':'+p['number'] for p in pp]]);continue
  _,ref,pin,x,y,points,blockers,layer=min(choices,key=lambda c:c[0])
  for t in blockers:removed.add(t['source']);tracks.remove(t)
  v={'net':net,'x':x,'y':y,'diameter':.45,'hole':.2};vias.append(v);newvias.append(v);assert addline(net,layer,points)
  escapes.append([net,ref,pin,len(blockers)]);print('ESCAPE',escapes[-1],flush=True)
print('ESCAPED',len(escapes),'RIPUP',len(removed),'NO ESCAPE',noescape,flush=True)
failed=[]
for ni,net in enumerate(allnets):
 if net=='GND':continue
 gs=groups(net);edges=0
 while len(gs)>1:
  choices=[]
  for i,a in enumerate(gs):
   for j in range(i):
    b=gs[j]
    for pa in a:
     pb=min(b,key=lambda z:math.dist(pa[:2],z[:2]));choices.append((math.dist(pa[:2],pb[:2]),i,j,pa,pb))
  success=False
  for dist,i,j,a,b in sorted(choices)[:8]:
   # Main high-current paths were routed first; resistive feedback branches carry negligible current.
   w=.6 if net.startswith('VIN') else .254 if net in ['VDD_3V3','VDD_4G','SIM_VDD','LTE_VDD_EXT'] else .1524
   if net=='VDD_4G' and any(p['ref'].startswith('R') or p['ref']=='C95' for p in pads if p['net']==net and any(math.dist((p['x'],p['y']),q[:2])<.01 for q in [a,b])):w=.1524
   common=(layers if a[2]==12 else [a[2]]) if a[2]==b[2] or b[2]==12 else []
   if common and addline(net,common[0],[a[:2],b[:2]],w):success=True
   elif addroute(net,a,b,w,(1,2,16)):success=True
   elif addroute(net,a,b,w,(1,16,2)):success=True
   if success:gs[j].extend(gs[i]);gs.pop(i);edges+=1;break
  if not success:failed.append({'net':net,'groupsRemaining':len(gs),'representatives':[g[0] for g in gs]});break
 print(ni,net,'edges',edges,'groups',len(gs),flush=True)
# Return complete replacement for the provisional remaining routes; original protected critical/interface geometry stays.
kept=[r for i,r in enumerate(base) if i not in removed and i>=51]
# The number of protected geometries is obtained from the original plans rather than assumed.
protected_count=sum(len(json.load(open(P/f'manifests/{n}.json',encoding='utf-8'))['routes']) for n in ['critical-routing-v13','interface-routing-v13'])
kept=[r for i,r in enumerate(base) if i not in removed and i>=protected_count]
new[:]=kept+new
newvias[:]=[v for n in ['remaining-routing-v13','ground-fanout-v13'] for v in json.load(open(P/f'manifests/{n}.json',encoding='utf-8'))['vias']]+newvias
save_plan('remaining-repaired-v13',failed)
(P/'manifests/repair-summary-v13.json').write_text(json.dumps({'removed':sorted(removed),'escapes':escapes,'noescape':noescape,'failed':failed},indent=2),encoding='utf-8')
