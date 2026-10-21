from pathlib import Path
exec(Path('PCB/scripts/optimize-trunks-v13.py').read_text(encoding='utf-8-sig').rsplit('\nprotected=',1)[0])
for net in ['RS485_B_EXT','RS485_A','ESP_BOOT','MCU_LTE_RX','RS485_B','MCU_485_DE','SIM_CLK','FIELD_TX','LTE_RXD','ESP_STRAP27']:
 start=time.time();oldrs=[r for r in plan['routes'] if r['net']==net];oldvs=[v for v in plan['vias'] if v['net']==net];print('MULTILAYER TRUNK',net,len(oldvs),flush=True)
 result=trunk(net,2,allowed=(2,16))
 if result is None:print('no improvement',flush=True);continue
 rs,vs=result
 if len(vs)>=len(oldvs) or length(rs)>length(oldrs)*1.10+2:print('reject',len(vs),length(rs),flush=True);continue
 record={'net':net,'method':'keep-top-reduce-trunk-transitions','accepted':True,'oldVias':len(oldvs),'newVias':len(vs),'oldLengthMm':round(length(oldrs),3),'newLengthMm':round(length(rs),3),'seconds':round(time.time()-start,1)}
 plan['routes']=[r for r in plan['routes'] if r['net']!=net]+rs;plan['vias']=[v for v in plan['vias'] if v['net']!=net]+vs;log.append(record);print(record,flush=True)
 OUT.write_text(json.dumps(plan,indent=2));(P/'manifests/routing-optimization-log-v13.json').write_text(json.dumps(log,indent=2))
print('TOTAL',len(plan['vias']),flush=True)

