from pathlib import Path
exec(Path('PCB/scripts/router-v12.py').read_text(encoding='utf-8'))
load_plan(P/'manifests/rf-routing-v12.json');load_plan(P/'manifests/usb-routing-v12.json')
for net,ref,a,target in [('ESP_USB_DM_EXT','R16',(24.45,34.0),(24.9,35.5)),('LTE_USB_DM_EXT','R61',(15.5,42.9),(17.4,47.1))]:
 obs=unary_union([obstacles(net,k) for k in layers])
 if net.startswith('LTE'):
  opts=[]
  own=unary_union([p['geom'] for p in pads if p['net']==net])
  for dx in np.arange(-2,2.01,.1):
   for dy in np.arange(-2,2.01,.1):
    b=(round(xy(ref,'2')[0]+dx,2),round(xy(ref,'2')[1]+dy,2))
    if Point(*b).distance(obs)>=.378 and Point(*b).distance(own)>=.275 and LineString([xy(ref,'2'),b]).distance(obstacles(net,2))>=.2546:opts.append((math.dist(b,xy(ref,'2')),b))
  if not opts:
   for w in [.2032,.1524,.127]:
    if addroute(net,(*xy(ref,'2'),2),(*target,16),w,(2,16)):
     print('LTE bridge routed',w,flush=True);break
   else:raise Exception('No escape via or route')
   continue
  a=min(opts)[1]
  print('LTE escape',a,flush=True)
 d=Point(*a).distance(obs)
 if d<.378:raise Exception(f'Via {net} clearance {d}')
 v={'net':net,'x':a[0],'y':a[1],'diameter':.45,'hole':.2};vias.append(v);newvias.append(v)
 if not addline(net,2,[xy(ref,'2'),a],.2032):raise Exception('Source blocked '+net)
 if not addroute(net,(*a,16),(*target,16),.24,(16,)):raise Exception('Inner bridge blocked '+net)
 print('Connected',net,flush=True)
save_plan('usb-final-bridge-v12')
