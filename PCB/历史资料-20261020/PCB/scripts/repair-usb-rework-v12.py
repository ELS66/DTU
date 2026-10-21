from pathlib import Path
exec(Path('PCB/scripts/router-v12.py').read_text(encoding='utf-8'))
load_plan(P/'manifests/rf-routing-v12.json')
p=json.load(open(P/'manifests/usb-routing-v12.json')); removed=p['routes'].pop(23)
for r in p['routes']:tracks.append({'net':r['net'],'layer':r['layer'],'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2)})
vias.extend(p['vias'])
net='ESP_USB_DM_EXT';a=(24.45,34.0);v={'net':net,'x':a[0],'y':a[1],'diameter':.45,'hole':.2};vias.append(v);newvias.append(v)
assert addline(net,2,[xy('R16','2'),a],.2032)
assert addroute(net,(*a,16),(24.9,35.5,16),.24,(16,))
for net,ref,target in [('LTE_USB_DM_EXT','R61',(18.,43.7)),('LTE_USB_DP_EXT','R60',(17.6,43.7))]:
 for w in [.24,.2032,.1524]:
  if addroute(net,(*xy(ref,'2'),2),(*target,2),w,(1,2,16)):
   print('Routed',net,w,flush=True);break
 else:raise Exception('Failed '+net)
save_plan('usb-rework-v12')
(P/'manifests/usb-routing-retained-v12.json').write_text(json.dumps(p,indent=2))
# Exactly identify the removed loop in the native snapshot.
native=json.load(open(P/'manifests/routing-current-v12.json'))['result']
ids=[r['id'] for r in native['polys'] if r['net']=='LTE_USB_DP_EXT' and r['layer']==2 and len(r['polygon'])>50]
assert len(ids)==1,ids
guard=(P/'scripts/read-pcb-pads-v12.js').read_text().split('const out=')[0]
(P/'scripts/remove-usb-loop-v12.js').write_text(guard+'if(!await eda.pcb_PrimitivePolyline.delete('+json.dumps(ids)+'))throw Error("USB rework failed");return {removed:'+json.dumps(ids)+'};')
