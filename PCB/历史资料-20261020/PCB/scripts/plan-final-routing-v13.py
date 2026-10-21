from pathlib import Path
exec(Path('PCB/scripts/router-v13.py').read_text(encoding='utf8'))
protected_routes=[];protected_vias=[]
for name in ['critical-routing-v13','interface-routing-v13']:
 a=load_plan(P/f'manifests/{name}.json');protected_routes+=a['routes'];protected_vias+=a['vias']
for t in tracks:t['protected']=True
base=json.load(open(P/'manifests/remaining-repaired-v13.json',encoding='utf8'))
affected={p['net'] for p in pads if p['ref'] in ['C52','RN2','RN5'] and p['net'] and p['net']!='GND'}
for t in base['routes']:
 for p in pads:
  if p['ref'] not in ['C52','RN2','RN5']:continue
  if t['net']!=p['net'] and t['layer'] in [1,12] and LineString(t['pointsMm']).distance(p['geom'])<t['widthMm']/2+.153:affected.add(t['net'])
for v in base['vias']:
 for p in pads:
  if p['ref'] in ['C52','RN2','RN5'] and p['net']!=v['net'] and Point(v['x'],v['y']).distance(p['geom'])<v['diameter']/2+.153:affected.add(v['net'])
print('REROUTE',sorted(affected),flush=True)
kept=[r for r in base['routes'] if r['net'] not in affected];kept_vias=[v for v in base['vias'] if v['net'] not in affected]
for t in kept:tracks.append({'net':t['net'],'layer':t['layer'],'geom':LineString(t['pointsMm']).buffer(t['widthMm']/2),'points':t['pointsMm']})
vias+=kept_vias
exec('def groups(net):'+Path('PCB/scripts/plan-remaining-routing-v13.py').read_text(encoding='utf8').split('def groups(net):')[1].split('power={')[0])
# Restore the RF protection branch before routing ordinary logic.
a=(*xy('J5','2'),1);b=(*xy('D10','1'),1)
rf_ok=addline('LTE_RF_FEED',1,[a[:2],b[:2]],.35) or addroute('LTE_RF_FEED',a,b,.35,(1,))
print('RF protection connection',rf_ok,flush=True)
failed=[]
# All exposed ground pads need a physical connection to a ground via or PTH.
for p in [p for p in pads if p['net']=='GND' and p['ref'] in ['C52','U2','D10']]:
 if p['ref']=='U2' and p['number']!='95':continue
 src=(p['x'],p['y'],p['layer']);ok=False
 for v in sorted([v for v in vias if v['net']=='GND'],key=lambda v:math.dist(src[:2],(v['x'],v['y'])))[:10]:
  dst=(v['x'],v['y'],1)
  if addline('GND',1,[src[:2],dst[:2]],.2) or addroute('GND',src,dst,.2,(1,)):ok=True;break
 if not ok:
  v=addvia('GND',src[:2],.45,.2,src[:2],1,.2);ok=v is not None
 print('GND repair',p['ref'],p['number'],ok,flush=True)
 if not ok:failed.append({'net':'GND','ref':p['ref'],'pin':p['number']})
ignore={'GND','LTE_RF_FEED','LTE_ANT'}|{f'{a}_USB_{b}{c}' for a in ['ESP','LTE'] for b in ['DP','DM'] for c in ['','_EXT']}
nets=sorted({p['net'] for p in pads if p['net'] and p['net'] not in ignore},key=lambda n:(n not in affected,n))
for ni,net in enumerate(nets):
 gs=groups(net);edges=0
 while len(gs)>1:
  choices=[]
  for i,a in enumerate(gs):
   for j in range(i):
    b=gs[j]
    for pa in a:
     pb=min(b,key=lambda z:math.dist(pa[:2],z[:2]));choices.append((math.dist(pa[:2],pb[:2]),i,j,pa,pb))
  success=False
  for dist,i,j,a,b in sorted(choices)[:5]:
   w=.6 if net.startswith('VIN') else .3 if net in ['VDD_3V3','VDD_4G','LTE_VDD_EXT','SIM_VDD'] else .1524
   if net=='VDD_4G' and any(p['ref'].startswith('R') or p['ref']=='C95' for p in pads if p['net']==net and any(math.dist((p['x'],p['y']),q[:2])<.01 for q in [a,b])):w=.2
   common=(layers if a[2]==12 else [a[2]]) if a[2]==b[2] or b[2]==12 else []
   if common and addline(net,common[0],[a[:2],b[:2]],w):success=True
   elif addroute(net,a,b,w,(1,2,16)):success=True
   if success:gs[j].extend(gs[i]);gs.pop(i);edges+=1;break
  if not success:failed.append({'net':net,'groupsRemaining':len(gs),'representatives':[g[0] for g in gs]});break
 if edges or len(gs)>1:print(ni,net,'edges',edges,'groups',len(gs),flush=True)
new[:]=protected_routes+kept+new
newvias[:]=protected_vias+kept_vias+newvias
save_plan('final-routing-v13',failed)
