from pathlib import Path
exec(Path('PCB/scripts/load-native-routing-large-v12.py').read_text(encoding='utf-8-sig').replace('routing-power-large-v12.json','routing-resume-large-v12.json'))
rp=json.load(open(P/'manifests/escape-ripup-large-v12.json'));removed=rp['removed'];rs=[r for r in native['polys'] if r['layer'] in layers and r['net']]
assert len(rs)==len(tracks)
tracks[:]=[t for t,r in zip(tracks,rs) if r['id'] not in removed]
vias[:]=[v for v in vias if not(v['net']=='VDD_4G' and math.dist((v['x'],v['y']),(26.2,27.1))<.001)]
load_plan(P/'manifests/local-repair-large-v12.json');load_plan(P/'manifests/escape-fanout-large-v12.json')
plan=json.load(open(P/'manifests/complete-repair-large-v12.json'));power={'VIN_485','VDD_3V3'}
oldnew=[r for r in plan['routes'] if r['net'] not in power];oldvias=[v for v in plan['vias'] if v['net'] not in power]
for r in oldnew:tracks.append({'net':r['net'],'layer':r['layer'],'points':r['pointsMm'],'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2)})
vias.extend(oldvias)
exec('def groups(net):'+Path('PCB/scripts/plan-remaining-routing-large-v12.py').read_text(encoding='utf-8-sig').split('def groups(net):')[1].split('power={')[0])
layers=[1,2,15,16];baseobs=obstacles
def obstacles(net,layer,ignore=()):
 g=baseobs(net,layer,ignore)
 if layer==15 and net!='GND':g=unary_union([g,box(16.4,54.8,24,61.5),box(27.3,38,35,43.4),box(27.8,42.5,29.6,60.2),box(28,58.8,42.7,64.7),box(17.8,60.2,20,65),box(6.5,58,14.5,65.5)])
 return g
for net,width in [('VIN_485',.6),('VDD_3V3',.254)]:
 gs=groups(net)
 while len(gs)>1:
  choices=sorted((math.dist(a[:2],b[:2]),i,j,a,b) for i,g in enumerate(gs) for j,h in enumerate(gs[:i]) for a in g for b in h)
  success=False
  for _,i,j,a,b in choices[:24]:
   if a[2]==b[2] and addline(net,a[2],[a[:2],b[:2]],width):success=True
   else:
    result=route(net,a,b,width,(1,2,15,16),limit=450000)
    if result:
     rr,vv=result
     for r in rr:new.append(r);tracks.append({'net':net,'layer':r['layer'],'points':r['pointsMm'],'geom':LineString(r['pointsMm']).buffer(width/2)})
     for x,y in vv:
      if not any(v['net']==net and Point(x,y).distance(Point(v['x'],v['y']))+.225<=v['diameter']/2+.01 for v in vias):
       v={'net':net,'x':x,'y':y,'diameter':.45,'hole':.2};vias.append(v);newvias.append(v)
     success=True
   if success:gs[j].extend(gs[i]);gs.pop(i);break
  if not success:raise Exception('Power reroute failed '+net)
 print('POWER',net,'groups',len(gs),flush=True)
new=oldnew+new;newvias=oldvias+newvias
save_plan('complete-repair-large-v12',plan['failed'])
for f in P.glob('scripts/apply-complete-repair-large-v12-*.js'):
 f.write_text(f.read_text(encoding='utf-8').replace("const layer=z.layer===1?EPCB_LayerId.TOP:z.layer===2?EPCB_LayerId.BOTTOM:EPCB_LayerId.INNER_2;","const layer=z.layer;"),encoding='utf-8')
