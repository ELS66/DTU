from pathlib import Path
exec(Path('PCB/scripts/router-v13.py').read_text(encoding='utf8'))
base=json.load(open(P/'manifests/usb-short-routing-v13.json',encoding='utf8'))
def rk(r):return (r['net'],r['layer'],round(r['widthMm'],6),tuple(tuple(round(v,6) for v in p) for p in r['pointsMm']))
def vk(v):return (v['net'],round(v['x'],6),round(v['y'],6))
protect_routes={rk(r) for n in ['critical-routing-v13','interface-routing-v13'] for r in json.load(open(P/f'manifests/{n}.json',encoding='utf8'))['routes']}
protect_vias={vk(v) for n in ['critical-routing-v13','interface-routing-v13'] for v in json.load(open(P/f'manifests/{n}.json',encoding='utf8'))['vias']}
protect_routes|={rk(r) for r in base['routes'] if r['net'] in ['LTE_ANT','LTE_RF_FEED'] or '_USB_' in r['net']}
protect_vias|={vk(v) for v in base['vias'] if '_USB_' in v['net']}
for r in base['routes']:tracks.append({'net':r['net'],'layer':r['layer'],'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2),'points':r['pointsMm'],'record':r,'protected':rk(r) in protect_routes})
for v in base['vias']:vias.append({**v,'protected':vk(v) in protect_vias or v['net']=='GND'})
exec('def groups(net):'+Path('PCB/scripts/plan-remaining-routing-v13.py').read_text(encoding='utf8').split('def groups(net):')[1].split('power={')[0])
ignore={'LTE_ANT','LTE_RF_FEED'}|{f'{a}_USB_{b}{c}' for a in ['ESP','LTE'] for b in ['DP','DM'] for c in ['','_EXT']}
allnets=sorted({p['net'] for p in pads if p['net'] and p['net'] not in ignore},key=lambda n:(n!='GND',n))
ripped=set();escaped=[];noescape=[]
def rip(net):
 global tracks,vias
 tracks=[t for t in tracks if t['net']!=net or t.get('protected') or 'record' not in t]
 vias=[v for v in vias if v['net']!=net or v.get('protected') or v in newvias]
 ripped.add(net)
for net in allnets:
 gs=groups(net)
 if len(gs)<2:continue
 for group in gs:
  if any(a[2]==12 or any(v['net']==net and math.dist(a[:2],(v['x'],v['y']))<.01 for v in vias) for a in group):continue
  pp=[p for p in pads if p['net']==net and any(math.dist(a[:2],(p['x'],p['y']))<.01 and a[2]==p['layer'] for a in group)]
  if not pp:continue
  static=unary_union([p['geom'] for p in pads if p['net']!=net]+holes)
  own=unary_union([p['geom'] for p in pads if p['net']==net]);choices=[]
  imm=unary_union([t['geom'] for t in tracks if t['net']!=net and t.get('protected')]+[Point(v['x'],v['y']).buffer(v['diameter']/2) for v in vias if v['net']!=net and v.get('protected')])
  for p in pp:
   surface=unary_union([q['geom'] for q in pads if q['net']!=net and q['layer'] in [12,p['layer']]]+holes+[t['geom'] for t in tracks if t['net']!=net and t.get('protected') and t['layer']==p['layer']]+[Point(v['x'],v['y']).buffer(v['diameter']/2) for v in vias if v['net']!=net and v.get('protected')])
   for radius in [.55,.7,.9,1.1,1.4,1.8,2.2,2.8,3.5,4.5,6]:
    for k in range(48):
     x=round((p['x']+radius*math.cos(k*math.pi/24))/.05)*.05;y=round((p['y']+radius*math.sin(k*math.pi/24))/.05)*.05;pt=Point(x,y)
     if not(.75<x<59.25 and .75<y<69.25) or pt.distance(static)<.225+.16 or pt.distance(own)<.225+.04 or pt.distance(imm)<.225+.16:continue
     dx=x-p['x'];dy=y-p['y'];diag=min(abs(dx),abs(dy))
     alternatives=[[(p['x'],p['y']),(p['x']+math.copysign(diag,dx),p['y']+math.copysign(diag,dy)),(x,y)],[(p['x'],p['y']),(x,p['y']),(x,y)],[(p['x'],p['y']),(p['x'],y),(x,y)]]
     for points in alternatives:
      line=LineString(points)
      if line.distance(surface)<.0762+.153:continue
      blocked={t['net'] for t in tracks if t['net']!=net and not t.get('protected') and ((t['layer']==p['layer'] and line.distance(t['geom'])<.0762+.16) or pt.distance(t['geom'])<.225+.16)}
      blocked|={v['net'] for v in vias if v['net']!=net and not v.get('protected') and (pt.distance(Point(v['x'],v['y']).buffer(v['diameter']/2))<.225+.16 or line.distance(Point(v['x'],v['y']).buffer(v['diameter']/2))<.0762+.16)}
      if 'GND' in blocked or len(blocked)>4:continue
      choices.append((len(blocked)*50+radius,p['ref'],p['number'],x,y,points,blocked,p['layer']))
    if choices and min(c[0] for c in choices)<2:break
  if not choices:noescape.append([net,[p['ref']+':'+p['number'] for p in pp]]);continue
  _,ref,pin,x,y,points,blocked,layer=min(choices,key=lambda c:c[0])
  for n in blocked:rip(n)
  v={'net':net,'x':x,'y':y,'diameter':.45,'hole':.2,'protected':False};vias.append(v);newvias.append(v)
  assert addline(net,layer,points)
  escaped.append([net,ref,pin,sorted(blocked)]);print('ESCAPE',escaped[-1],flush=True)
print('NOESCAPE',noescape,'RIPPED',sorted(ripped),flush=True)
failed=[]
for ni,net in enumerate(allnets):
 if net=='GND':continue
 gs=groups(net);edges=0
 while len(gs)>1:
  choices=[]
  for i,aa in enumerate(gs):
   a=[q for q in aa if q[2]==12 or (q[2] in [2,16] and any(v['net']==net and math.dist((v['x'],v['y']),q[:2])<.01 for v in vias))] or aa
   for j in range(i):
    bb=gs[j]
    b=[q for q in bb if q[2]==12 or (q[2] in [2,16] and any(v['net']==net and math.dist((v['x'],v['y']),q[:2])<.01 for v in vias))] or bb
    for pa in a:
     pb=min(b,key=lambda z:math.dist(pa[:2],z[:2]));choices.append((math.dist(pa[:2],pb[:2]),i,j,pa,pb))
  success=False
  for dist,i,j,a,b in sorted(choices)[:5]:
   w=.6 if net.startswith('VIN') else .3 if net in ['VDD_3V3','VDD_4G','LTE_VDD_EXT','SIM_VDD'] else .1524
   if net=='VDD_4G' and any(p['ref'].startswith('R') or p['ref'] in ['C95','C81','C82','C83','C84'] for p in pads if p['net']==net and any(math.dist((p['x'],p['y']),q[:2])<.01 for q in [a,b])):w=.2
   common=(layers if a[2]==12 else [a[2]]) if a[2]==b[2] or b[2]==12 else []
   if common and addline(net,common[0],[a[:2],b[:2]],w):success=True
   elif addroute(net,a,b,w,(1,2,16)):success=True
   if success:gs[j].extend(gs[i]);gs.pop(i);edges+=1;break
  if not success:failed.append({'net':net,'groupsRemaining':len(gs),'representatives':[g[0] for g in gs]});break
 if edges or len(gs)>1:print('NET',ni,net,edges,len(gs),flush=True)
keep=[t['record'] for t in tracks if 'record' in t]
new[:]=keep+new
newvias[:]=[{k:v for k,v in z.items() if k!='protected'} for z in vias]
save_plan('surgical2-routing-v13',failed)
(P/'manifests/surgical2-summary-v13.json').write_text(json.dumps({'escaped':escaped,'noescape':noescape,'ripped':sorted(ripped)},indent=2))
