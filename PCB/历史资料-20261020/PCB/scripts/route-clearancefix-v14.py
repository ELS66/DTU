"""Plan new upper-board copper while preserving lower connector geometry."""
from pathlib import Path
import json,copy,math,collections
s=Path('PCB/scripts/router-v13.py').read_text(encoding='utf8').replace('read-pcb-pads-v13.json','clearancefix-staged-pads-v14.json').replace('(4,66),(56,66)','(4,71),(56,71)').replace('ny=701','ny=751').replace('69.5','74.5').replace('69.25','74.25')
exec(s)
from shapely.strtree import STRtree
M=P/'manifests';base=json.loads((M/'ml307fix-actual-routing-v13.json').read_text(encoding='utf8'));oldcs=json.loads((M/'ml307fix-final-pads-v13.json').read_text(encoding='utf8'))['result'];oldby={c['ref']:c for c in oldcs}
shifts={q['ref']:q['deltaMm'] for q in json.loads((M/'clearancefix-stage-v14.json').read_text(encoding='utf8'))['componentMoves']}
def ty(y):
 if y>=61:return y+3.2
 if y>=60:return y+2+1.2*(y-60)
 if y>=44:return y+2
 if y>=43:return y+2*(y-43)
 return y
pointmoves=[]
for c in cs:
 if c['ref'] not in shifts:continue
 old=oldby[c['ref']]
 for p in c['pads']:
  op=next(q for q in old['pads'] if q['number']==p['number']);pointmoves.append((p['net'],(op['x']*.0254,op['y']*.0254),(p['x']*.0254,p['y']*.0254)))
via_plan=[{**v,'y':ty(v['y'])} for v in base['vias']]
pad_union=unary_union([p['geom'] for p in pads]);via_targets={};chosen=[]
for v,old in zip(via_plan,base['vias']):
 if old['y']<43:continue
 pt=Point(v['x'],v['y']);near=min((pt.distance(p['geom']),p['net']) for p in pads)
 # Keep all upper vias clear of solder-mask openings, including same-net lands.
 if near[0]<.432 or any(math.dist((v['x'],v['y']),q)<.49 for q in chosen):
  opts=[]
  for radius in [0,.1,.2,.3,.4,.5,.7,.9,1.2,1.5,2,2.5,3]:
   for i in range(64):
    x=round(v['x']+radius*math.cos(i*math.pi/32),3);y=round(v['y']+radius*math.sin(i*math.pi/32),3);q=Point(x,y)
    if not(.75<x<59.25 and .75<y<74.25) or q.distance(pad_union)<.435:continue
    if any(q.distance(h)<.23 for h in holes):continue
    if any(math.dist((x,y),(other['x'],other['y']))<.49 for other in via_plan if other['id']!=v['id']):continue
    if any(math.dist((x,y),q)<.49 for q in chosen):continue
    opts.append((math.dist((x,y),(v['x'],v['y'])),x,y))
   if opts:break
  if not opts:raise RuntimeError('No via site '+v['id'])
  _,v['x'],v['y']=min(opts)
 chosen.append((v['x'],v['y']))
for old,v in zip(base['vias'],via_plan):
 if math.dist((old['x'],old['y']),(v['x'],v['y']))>.0001:
  via_targets[v['id']]=[v['x'],v['y']];pointmoves.insert(0,(v['net'],(old['x'],old['y']),(v['x'],v['y'])))
def movedpoint(net,pt):
 for n,old,newp in pointmoves:
  if n==net and math.dist(pt,old)<.018:return list(newp)
 return [pt[0],ty(pt[1])]
initial=[{**r,'pointsMm':[movedpoint(r['net'],q) for q in r['pointsMm']]} for r in base['routes']]
# The endpoints of one conductor must share exactly the same transformed coordinate.
# Resolve non-pad branch nodes that became buried in a different-net pad.
nodes={}
for r in initial:
 for pt in [r['pointsMm'][0],r['pointsMm'][-1]]:nodes.setdefault((r['net'],round(pt[0],5),round(pt[1],5)),[]).append(r)
node_moves={}
for (net,x,y),rs in nodes.items():
 if y<42.9:continue
 layerwidth={r['layer']:max(q['widthMm'] for q in rs if q['layer']==r['layer']) for r in rs}
 def clear(q):
  return all(q.distance(p['geom'])>=w/2+.155 for lay,w in layerwidth.items() for p in pads if p['net']!=net and p['layer'] in [lay,12]) and all(q.distance(Point(v['x'],v['y']))>=max(layerwidth.values())/2+v['diameter']/2+.155 for v in via_plan if v['net']!=net)
 if clear(Point(x,y)):continue
 # Via/pad anchors were deliberately placed already; do not silently detach them.
 if any(n==net and math.dist((x,y),newp)<.01 for n,old,newp in pointmoves):continue
 opts=[]
 for radius in [.1,.2,.3,.4,.6,.8,1,1.5,2]:
  for i in range(32):
   xx=round(x+radius*math.cos(i*math.pi/16),3);yy=round(y+radius*math.sin(i*math.pi/16),3)
   if clear(Point(xx,yy)):opts.append((radius,xx,yy))
  if opts:break
 if not opts:raise RuntimeError('Branch node blocked '+str((net,x,y)))
 _,xx,yy=min(opts);node_moves[(net,x,y)]=[xx,yy]
for r in initial:
 for i,pt in enumerate(r['pointsMm']):
  r['pointsMm'][i]=node_moves.get((r['net'],round(pt[0],5),round(pt[1],5)),pt)
selected={};kept=[]
for r in initial:
 g=LineString(r['pointsMm']).buffer(r['widthMm']/2)
 bad=any(g.distance(p['geom'])<.154 for p in pads if p['net']!=r['net'] and p['layer'] in [r['layer'],12]) or any(g.distance(Point(v['x'],v['y']).buffer(v['diameter']/2))<.154 for v in via_plan if v['net']!=r['net']) or any(g.distance(h)<.01 for h in holes)
 if bad:selected[r['id']]=r
 else:kept.append(r)
# Reroute the shorter member of each newly conflicting pair; preserve unchanged lower copper.
for _ in range(2):
 gs=[LineString(r['pointsMm']).buffer(r['widthMm']/2) for r in kept];tree=STRtree(gs);remove=set()
 for i,r in enumerate(kept):
  for jj in tree.query(gs[i].buffer(.152)):
   j=int(jj);q=kept[j]
   if j>=i or r['net']==q['net'] or r['layer']!=q['layer']:continue
   gap=gs[i].distance(gs[j])
   if gap>=.1515:continue
   pick=i if max(p[1] for p in r['pointsMm'])>42 else j
   remove.add(kept[pick]['id'])
 for r in kept:
  if r['id'] in remove:selected[r['id']]=r
 kept=[r for r in kept if r['id'] not in remove]
print('Initial transformed tracks',len(initial),'reroute',len(selected),'moved vias',len(via_targets),'branch shifts',len(node_moves),flush=True)
for r in kept:tracks.append({'net':r['net'],'layer':r['layer'],'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2),'points':r['pointsMm']})
vias.extend(via_plan)
jobs=list(selected.values());jobs.sort(key=lambda r:(r['net'] not in ['LTE_ANT','LTE_RF_FEED'],not ('USB' in r['net']),r['net'] not in ['VDD_4G','GND'],r['net']=='GND',-r['widthMm'],len(r['pointsMm'])))
failed=[]
for n,r in enumerate(jobs):
 aa,bb=r['pointsMm'][0],r['pointsMm'][-1];layer=r['layer'];w=r['widthMm']
 if math.dist(aa,bb)<.001:continue
 if addline(r['net'],layer,[aa,bb],w):ok=True
 elif addroute(r['net'],(*aa,layer),(*bb,layer),w,(layer,)):ok=True
 elif r['net'] in ['LTE_ANT','LTE_RF_FEED']:ok=False
 else:ok=addroute(r['net'],(*aa,layer),(*bb,layer),w,tuple(dict.fromkeys([layer,1,2,16])))
 print(n,r['net'],r['id'],ok,'vias',len(newvias),flush=True)
 if not ok:failed.append(r)
result={'routes':kept+[{**r,'id':'clearance_new_'+str(i)} for i,r in enumerate(new)],'vias':via_plan+[{**v,'id':'clearance_via_'+str(i)} for i,v in enumerate(newvias)]}
(M/'clearancefix-rerouted-plan-v14.json').write_text(json.dumps(result,indent=2),encoding='utf8')
(M/'clearancefix-routing-diff-v14.json').write_text(json.dumps({'reroutedIds':list(selected),'viaTargets':via_targets,'branchMoves':[{'net':n,'from':[x,y],'to':v} for (n,x,y),v in node_moves.items()],'newRoutes':new,'newVias':newvias,'failed':failed},indent=2),encoding='utf8')
print('RESULT',len(result['routes']),len(result['vias']),'FAILED',len(failed),flush=True)
