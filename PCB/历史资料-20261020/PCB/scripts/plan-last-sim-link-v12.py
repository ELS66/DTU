from pathlib import Path
exec(Path('PCB/scripts/load-native-routing-large-v12.py').read_text(encoding='utf-8-sig').replace('routing-power-large-v12.json','routing-pass3-large-v12.json').replace('step=.1;nx=601;ny=701','layers=[1,2,15,16];step=.1;nx=601;ny=701'))
exec('def groups(net):'+Path('PCB/scripts/plan-remaining-routing-large-v12.py').read_text(encoding='utf-8-sig').split('def groups(net):')[1].split('power={')[0])
net='SIM_RST_M';print('groups',groups(net),flush=True)
# Join the two opposing, same-net pad edges with a filled/capped 0.2 mm drill.
# The signal via, like the existing module thermal-pad vias, requires VIPPO.
obs=unary_union([obstacles(net,k) for k in layers]);options=[];surface=obstacles(net,1)
for x in np.arange(22.25,22.851,.05):
 for y in np.arange(42,44.351,.05):
  pt=(float(x),float(y))
  if Point(pt).distance(obs)<.225+.16:continue
  if not all(math.dist(pt,(v['x'],v['y']))>(.2+v['hole'])/2+.3 for v in vias):continue
  p=next(p for p in pads if p['ref']=='U2' and p['number']=='12')
  if LineString([(p['x'],p['y']),pt]).distance(surface)<.0762+.153:continue
  options.append((abs(y-42.794)+abs(x-22.54),pt))
print('Via choices count',len(options),flush=True)
assert options
_,pt=min(options)
assert all(math.dist(pt,(v['x'],v['y']))>(.2+v['hole'])/2+.3 for v in vias)
v={'net':net,'x':pt[0],'y':pt[1],'diameter':.45,'hole':.2};vias.append(v);newvias.append(v)
for ref,pin in [('U2','12')]:
 p=next(p for p in pads if p['ref']==ref and p['number']==pin)
 assert addline(net,p['layer'],[(p['x'],p['y']),pt])
if len(groups(net))>1:
 a=next(v for v in vias if v['net']==net and abs(v['x']-22.8)<.001 and abs(v['y']-40.55)<.001)
 result=route(net,(a['x'],a['y'],15),(pt[0],pt[1],15),.1524,(15,),limit=100000)
 assert result
 rr,vv=result;assert not vv
 for r in rr:new.append(r);tracks.append({'net':net,'layer':r['layer'],'geom':LineString(r['pointsMm']).buffer(.0762)})
assert len(groups(net))==1
save_plan('last-sim-link-v12')
for f in P.glob('scripts/apply-last-sim-link-v12-*.js'):
 f.write_text(f.read_text(encoding='utf-8').replace("const layer=z.layer===1?EPCB_LayerId.TOP:z.layer===2?EPCB_LayerId.BOTTOM:EPCB_LayerId.INNER_2;","const layer=z.layer;"),encoding='utf-8')
(P/'reports/盘中过孔工艺-V0.12.json').write_text(json.dumps({'signalVia':{'net':net,'xMm':pt[0],'yMm':pt[1],'holeMm':.2,'diameterMm':.45},'requirement':'该信号过孔及模组中心地焊盘中的过孔采用树脂填孔、电镀盖帽、表面整平（VIPPO）；不要按普通开放过孔直接回流装配。'},ensure_ascii=False,indent=2),encoding='utf-8')
