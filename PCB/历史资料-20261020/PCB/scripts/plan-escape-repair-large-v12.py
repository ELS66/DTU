from pathlib import Path
exec(Path('PCB/scripts/load-native-routing-large-v12.py').read_text(encoding='utf-8-sig').replace('routing-power-large-v12.json','routing-resume-large-v12.json'))
vias[:]=[v for v in vias if not(v['net']=='VDD_4G' and math.dist((v['x'],v['y']),(26.2,27.1))<.001)]
for t,r in zip(tracks,native['polys'][1:]):pass
# Preserve primitive identities for selective rip-up; outline has no electrical net.
rs=[r for r in native['polys'] if r['layer'] in layers and r['net']]
assert len(rs)==len(tracks)
for t,r in zip(tracks,rs):t['id']=r['id']
load_plan(P/'manifests/local-repair-large-v12.json')
exec('def groups(net):'+Path('PCB/scripts/plan-remaining-routing-large-v12.py').read_text(encoding='utf-8-sig').split('def groups(net):')[1].split('power={')[0])
protected={'GND','LTE_ANT','LTE_RF_FEED'}|{f'{a}_USB_{b}{c}' for a in ['ESP','LTE'] for b in ['DP','DM'] for c in ['','_EXT']}
removed={};escaped=[]
nets=['SIM_DATA_M','LTE_PWRKEY','LTE_RX_SER','MCU_LTE_PWRKEY','232_RIN','MCU_485_DE','SIM_DET','SIM_DATA','FIELD_TX']
for net in nets:
 gs=groups(net)
 if len(gs)==1:continue
 for group in gs:
  if any(math.dist(a[:2],(v['x'],v['y']))<.01 for a in group for v in vias if v['net']==net):continue
  pp=[p for p in pads if p['net']==net and any(math.dist(a[:2],(p['x'],p['y']))<.01 and a[2]==p['layer'] for a in group)]
  padobs=unary_union([p['geom'] for p in pads if p['net']!=net]+holes+[Point(v['x'],v['y']).buffer(max(v['diameter']/2,(v['hole']+.2)/2+.3-.153)) for v in vias])
  own=unary_union([p['geom'] for p in pads if p['net']==net])
  choices=[]
  for p in pp:
   surface=unary_union([q['geom'] for q in pads if q['net']!=net and q['layer'] in [12,p['layer']]]+holes+[Point(v['x'],v['y']).buffer(v['diameter']/2) for v in vias if v['net']!=net])
   for radius in [.6,.8,1,1.2,1.5,1.8,2.2,2.8,3.5,4.5]:
    for k in range(48):
     x=round((p['x']+radius*math.cos(k*math.pi/24))/.05)*.05;y=round((p['y']+radius*math.sin(k*math.pi/24))/.05)*.05
     pt=Point(x,y)
     if not(.75<x<59.25 and .75<y<69.25) or pt.distance(padobs)<.225+.16 or pt.distance(own)<.225+.04:continue
     # Prefer 45-degree or orthogonal fan-outs where possible.
     dx=x-p['x'];dy=y-p['y'];diag=min(abs(dx),abs(dy));mid=(p['x']+math.copysign(diag,dx),p['y']+math.copysign(diag,dy))
     line=LineString([(p['x'],p['y']),mid,(x,y)])
     if line.distance(surface)<.0762+.153:continue
     blockers=[t for t in tracks if t['net']!=net and ((t['layer']==p['layer'] and line.distance(t['geom'])<.0762+.16) or pt.distance(t['geom'])<.225+.16)]
     if any(t['net'] in protected or not t.get('id') for t in blockers) or len(blockers)>3:continue
     score=len(blockers)*100+sum(t['geom'].area for t in blockers)*.1+radius
     choices.append((score,p['ref'],p['number'],x,y,list(line.coords),blockers,p['layer']))
  if not choices:
   print('NO ESCAPE',net,[p['ref']+':'+p['number'] for p in pp],flush=True);continue
  best=min(choices,key=lambda c:c[0]);_,ref,pin,x,y,points,blockers,layer=best
  for t in blockers:removed[t['id']]=t['net'];tracks.remove(t)
  v={'net':net,'x':x,'y':y,'diameter':.45,'hole':.2};vias.append(v);newvias.append(v)
  assert addline(net,layer,points)
  escaped.append({'net':net,'ref':ref,'pin':pin,'x':x,'y':y,'removed':[t['id'] for t in blockers]})
  print('ESCAPE',escaped[-1],flush=True)
(P/'manifests/escape-ripup-large-v12.json').write_text(json.dumps({'removed':removed,'escaped':escaped},indent=2),encoding='utf-8')
save_plan('escape-fanout-large-v12')
