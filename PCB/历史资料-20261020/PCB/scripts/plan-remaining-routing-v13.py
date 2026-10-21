from pathlib import Path
exec(Path('PCB/scripts/router-v13.py').read_text(encoding='utf-8'))
load_plan(P/'manifests/critical-routing-v13.json')
load_plan(P/'manifests/interface-routing-v13.json')
load_plan(P/'manifests/ground-fanout-v13.json')
ignored={'GND','LTE_ANT','LTE_RF_FEED'}|{f'{a}_USB_{b}{c}' for a in ['ESP','LTE'] for b in ['DP','DM'] for c in ['','_EXT']}
def groups(net):
 os=[]
 for p in pads:
  if p['net']==net:os.append({'geom':p['geom'],'ls':set(layers) if p['layer']==12 else {p['layer']},'pts':[(p['x'],p['y'],p['layer'])]})
 for v in vias:
  if v['net']==net:os.append({'geom':Point(v['x'],v['y']).buffer(v['diameter']/2),'ls':set(layers),'pts':[(v['x'],v['y'],k) for k in layers]})
 for t in tracks:
  if t['net']==net:os.append({'geom':t['geom'],'ls':{t['layer']},'pts':[(p[0],p[1],t['layer']) for p in [t['points'][0],t['points'][-1]]] if 'points' in t else []})
 parents=list(range(len(os)))
 def find(x):
  while parents[x]!=x:parents[x]=parents[parents[x]];x=parents[x]
  return x
 for i,a in enumerate(os):
  for j in range(i):
   b=os[j]
   if a['ls']&b['ls'] and a['geom'].distance(b['geom'])<.003:parents[find(i)]=find(j)
 gs={}
 for i,o in enumerate(os):gs.setdefault(find(i),[]).extend(o['pts'])
 return [list(dict.fromkeys(g)) for g in gs.values() if g]
power={'VDD_4G','VDD_3V3','VIN_PROT','VIN_IN','VIN_DIODE','VIN_TTL','VIN_OR','VIN_485','VIN_232','LTE_VDD_EXT','SIM_VDD','LTE_PWR_EN'}
nets=sorted({p['net'] for p in pads if p['net'] and p['net'] not in ignored},key=lambda n:(0 if n in power else 1, len([p for p in pads if p['net']==n])))
failed=[]
for index,net in enumerate(nets):
 print("START",index,net,flush=True)
 gs=groups(net);edges=0
 while len(gs)>1:
  choices=[]
  for i,a in enumerate(gs):
   for j in range(i):
    b=gs[j]
    for pa in a:
     pb=min(b,key=lambda z:math.dist(pa[:2],z[:2]));choices.append((math.dist(pa[:2],pb[:2]),i,j,pa,pb))
  success=False
  for dist,i,j,a,b in sorted(choices)[:3]:
   w=.6 if net.startswith('VIN') or net=='VDD_4G' else .3 if net in power and net!='LTE_PWR_EN' else .1524
   if net=='VDD_4G' and any(p['ref'].startswith('R') or p['ref']=='C95' for p in pads if p['net']==net and any(math.dist((p['x'],p['y']),q[:2])<.01 for q in [a,b])):w=.2
   common=(layers if a[2]==12 else [a[2]]) if a[2]==b[2] or b[2]==12 else []
   if common and addline(net,common[0],[a[:2],b[:2]],w):success=True
   elif addroute(net,a,b,w):success=True
   if success:
    gs[j].extend(gs[i]);gs.pop(i);edges+=1;break
  if not success:failed.append({'net':net,'groupsRemaining':len(gs),'representatives':[g[0] for g in gs]});break
 print(index+1,net,'connections',edges,'groups',len(gs),'routes',len(new),'vias',len(newvias),flush=True)
 if (index+1)%10==0:save_plan('remaining-routing-v13',failed)
save_plan('remaining-routing-v13',failed)

