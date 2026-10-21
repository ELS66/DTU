from pathlib import Path
import json,copy,math
R=Path('PCB');M=R/'manifests';cs=json.loads((M/'ml307fix-master-pads-v13.json').read_text(encoding='utf8'))['result'];original=copy.deepcopy(cs)
shifts={'J5':(0,1.5),'C50':(1.65,3.35),'R50':(0,.8),'C51':(0,2.25),'R60':(0,.7),'R61':(0,.7)}
for c in cs:
 if c['ref'] not in shifts:continue
 dx,dy=shifts[c['ref']];c['x']+=dx/.0254;c['y']+=dy/.0254
 for p in c['pads']:p['x']+=dx/.0254;p['y']+=dy/.0254
(M/'ml307fix-proposed-pads-v13.json').write_text(json.dumps({'result':cs},indent=2),encoding='utf8');(M/'ml307fix-component-shifts-v13.json').write_text(json.dumps(shifts,indent=2),encoding='utf8')
plan=json.loads((M/'lead-hole-actual-routing-v13.json').read_text(encoding='utf8'))
for c in original:
 if c['ref'] in shifts:
  print(c['ref'])
  for p in c['pads']:
   if p['net']!='GND':continue
   for r in plan['routes']:
    if r['net']=='GND' and r['layer']==1 and any(math.dist(q,(p['x']*.0254,p['y']*.0254))<.015 for q in r['pointsMm']):
     vv=[v for v in plan['vias'] if v['net']=='GND' and any(math.dist(q,(v['x'],v['y']))<.01 for q in r['pointsMm'])];print(p['number'],r['id'],r['pointsMm'],[(v['id'],v['x'],v['y']) for v in vv])
s=(R/'scripts/check-routing-opt-actual-copper-v13.py').read_text(encoding='utf8').replace('read-pcb-pads-before-opt-v13.json','ml307fix-proposed-pads-v13.json').replace('routing-optimized-source-v13.json','lead-hole-actual-routing-v13.json').replace('routing-opt-actual-copper-check-v13.json','ml307fix-initial-copper-check-v13.json');exec(s)
