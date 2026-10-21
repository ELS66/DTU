from pathlib import Path
exec(Path('PCB/scripts/router-v13.py').read_text(encoding='utf8'))
base=load_plan(P/'manifests/surgical2-routing-v13.json')
original_route=route
route=lambda net,a,b,width=.1524,allowed=(1,2,16),limit=200000:original_route(net,a,b,width,allowed,limit)
failed=[]
# Use the existing fanout vias as endpoints, keeping the new interconnect away from component pads.
checks=[('TTL_RX_EXT',(27.4,11.5,2),(40.4,12.2,2),.1524,(2,16)),('RS485_B',(13.35,14.15,2),(36.1,10.8,2),.1524,(2,16))]
for net,a,b,w,allowed in checks:
 ok=addline(net,a[2],[a[:2],b[:2]],w) or addroute(net,a,b,w,allowed);print(net,'join',ok,flush=True)
 if not ok:failed.append(net)
# A short local bridge between existing vias; the ground fill clears this trace without cutting the plane across the board.
ok=addline('RS485_B',15,[(25.95,13),(27.3,12.2)],.1524);print('RS485_B local bridge',ok,flush=True)
if not ok:failed.append('RS485_B bridge')
new[:]=base['routes']+new;newvias[:]=base['vias']+newvias
save_plan('connected-routing-v13',failed)
