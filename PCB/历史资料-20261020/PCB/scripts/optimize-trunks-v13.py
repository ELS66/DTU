"""Keep validated top fanouts, connect them with one routing layer where possible."""
from pathlib import Path
import sys
sys.argv=['trunks','--resume']
exec(Path('PCB/scripts/optimize-routing-v13.py').read_text(encoding='utf8').split('protected=')[0])

def trunk(net,layer,allowed=None):
 global tracks,vias
 allowed=allowed or (layer,)
 oldrs=[r for r in plan['routes'] if r['net']==net];oldvs=[v for v in plan['vias'] if v['net']==net]
 top=[r for r in oldrs if r['layer']==1]
 gs=[g for g in groups(net,top,[]) if any(o.get('pad') for o in g)]
 retained=[]
 for r in top:
  geom=LineString(r['pointsMm']).buffer(r['widthMm']/2)
  if any(any(geom.distance(o['geom'])<.001 for o in g) for g in gs):retained.append(r)
 tracks=[{'net':r['net'],'layer':r['layer'],'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2),'points':r['pointsMm']} for r in plan['routes'] if r['net']!=net]+[{'net':net,'layer':r['layer'],'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2),'points':r['pointsMm']} for r in retained]
 vias=[v for v in plan['vias'] if v['net']!=net];rs=list(retained);vs=[]
 for g in sorted(gs,key=lambda g:len(g)):
  if any(any(k in o['ls'] for k in allowed) for o in g):continue
  if any(any(Point(v['x'],v['y']).buffer(v['diameter']/2).distance(o['geom'])<.001 for o in g) for v in vs):continue
  candidates=[]
  pp=[p for o in g if o.get('pad') for p in o['pts']]
  for v in oldvs:
   if any(Point(v['x'],v['y']).buffer(v['diameter']/2).distance(o['geom'])<.001 for o in g):
    candidates.append((min(math.dist((v['x'],v['y']),p[:2]) for p in pp),v))
  if not candidates:return None
  v=min(candidates,key=lambda z:z[0])[1];vs.append(v);vias.append(v)
 gs=groups(net,rs,vs);attempt=0;width=max(.1524,min(r['widthMm'] for r in oldrs))
 while len(gs)>1:
  gs=[g for g in gs if any(o.get('pad') for o in g) or any(any(k in o['ls'] for k in allowed) for o in g)]
  if len(gs)<2:break
  choices=[]
  for i,a in enumerate(gs):
   for j in range(i):
    b=gs[j]
    aa=[p for o in a for p in o['pts'] if p[2] in (*allowed,12)];bb=[p for o in b for p in o['pts'] if p[2] in (*allowed,12)]
    for pa in aa:
     if bb:
      pb=min(bb,key=lambda q:math.dist(pa[:2],q[:2]));choices.append((math.dist(pa[:2],pb[:2]),pa,pb))
  success=False
  for d,a,b in sorted(choices)[:3]:
   same=[k for k in allowed if a[2] in [k,12] and b[2] in [k,12]]
   if same and LineString([a[:2],b[:2]]).distance(obstacles(net,same[0]))>width/2+.159:rout=([{'net':net,'layer':same[0],'widthMm':width,'pointsMm':[list(a[:2]),list(b[:2])]}],[])
   else:rout=pathfind(net,a,b,width,allowed=allowed,limit=60000)
   if rout is None:continue
   r,v=rout
   for z in r:rs.append(z);tracks.append({'net':net,'layer':z['layer'],'geom':LineString(z['pointsMm']).buffer(width/2),'points':z['pointsMm']})
   for x,y in v:
    if any(q['net']==net and math.dist((x,y),(q['x'],q['y']))<.04 for q in vias):continue
    z={'net':net,'x':x,'y':y,'diameter':.45,'hole':.2};vs.append(z);vias.append(z)
   success=True;break
  attempt+=1
  if not success or attempt>30:return None
  newgs=groups(net,rs,vs)
  if len(newgs)>=len(gs):return None
  gs=newgs
 if len([g for g in groups(net,rs,vs) if any(o.get('pad') for o in g)])!=1:return None
 return rs,vs

protected={'GND','VDD_3V3','VDD_4G','VIN_IN','VIN_DIODE','VIN_PROT','SIM_VDD','LTE_VDD_EXT','LTE_SW','LTE_BST','LTE_FB','MCU_LDO_FB','LTE_ANT','LTE_RF_FEED'}
counts=collections.Counter(v['net'] for v in plan['vias'])
nets=sorted([n for n in counts if n not in protected and 'USB' not in n and not n.startswith('232_C') and n!='232_VMINUS'],key=lambda n:-counts[n])
for net in nets:
 start=time.time();oldrs=[r for r in plan['routes'] if r['net']==net];oldvs=[v for v in plan['vias'] if v['net']==net];best=None
 print('TRUNK',net,len(oldvs),flush=True)
 for layer in [2,16]:
  result=trunk(net,layer)
  if result is None:continue
  rs,vs=result
  if len(vs)>=len(oldvs) or length(rs)>length(oldrs)*1.10+2:continue
  if best is None or (len(vs),length(rs))<(len(best[1]),length(best[0])):best=result
 if best:
  rs,vs=best;record={'net':net,'method':'keep-top-fanout','accepted':True,'oldVias':len(oldvs),'newVias':len(vs),'oldLengthMm':round(length(oldrs),3),'newLengthMm':round(length(rs),3),'seconds':round(time.time()-start,1)}
  plan['routes']=[r for r in plan['routes'] if r['net']!=net]+rs;plan['vias']=[v for v in plan['vias'] if v['net']!=net]+vs;log.append(record);print(record,flush=True)
  OUT.write_text(json.dumps(plan,indent=2));(P/'manifests/routing-optimization-log-v13.json').write_text(json.dumps(log,indent=2))
print('TOTAL VIAS',len(plan['vias']),flush=True)
