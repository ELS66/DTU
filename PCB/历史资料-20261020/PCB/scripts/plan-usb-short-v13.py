from pathlib import Path
exec(Path('PCB/scripts/router-v13.py').read_text(encoding='utf8'))
base=json.load(open(P/'manifests/surgical-routing-v13.json',encoding='utf8'))
changed={'LTE_USB_DP','LTE_USB_DM','LTE_USB_DP_EXT','LTE_USB_DM_EXT'}
region=box(20.7,53.6,25.2,62.2)
# Reserve the short internal USB route before ordinary logic.
for r in base['routes']:
 if r['net']!='GND' and r['layer'] in [1,2,16] and LineString(r['pointsMm']).buffer(r['widthMm']/2+.153).intersects(region) and r['net'] not in ['LTE_RF_FEED','LTE_ANT']:changed.add(r['net'])
for v in base['vias']:
 if v['net']!='GND' and region.intersects(Point(v['x'],v['y']).buffer(v['diameter']/2+.153)):changed.add(v['net'])
print('USB region reroute',sorted(changed),flush=True)
kept=[r for r in base['routes'] if r['net'] not in changed];kept_v=[v for v in base['vias'] if v['net'] not in changed]
for r in kept:tracks.append({'net':r['net'],'layer':r['layer'],'geom':LineString(r['pointsMm']).buffer(r['widthMm']/2),'points':r['pointsMm']})
vias+=kept_v
pairs=[('LTE_USB_DP','59','R60',(22.6,55.45),(24.35,58.75)),('LTE_USB_DM','60','R61',(21.4,55.45),(21,58.75))]
failed=[]
for net,pin,res,v1,v2 in pairs:
 a=xy('U2',pin);b=xy(res,'1')
 # Normal through vias outside the solder pads, identical via count on both signals.
 u=addvia(net,v1,.45,.2,a,1,.2);v=addvia(net,v2,.45,.2,b,1,.2)
 print(net,'vias',u,v,flush=True)
 if not u or not v or not(addline(net,2,[u,v],.45) or addroute(net,(*u,2),(*v,2),.45,(2,))):failed.append(net)
for net,res,ch,pin in [('LTE_USB_DP_EXT','R60','1','2'),('LTE_USB_DM_EXT','R61','2','3')]:
 for a,b in [(xy(res,'2'),xy('D20',ch)),(xy('D20',ch),xy('J7',pin))]:
  if not(addline(net,1,[a,b],.25) or addroute(net,(*a,1),(*b,1),.25,(1,2))):failed.append(net)
new[:]=kept+new
newvias[:]=kept_v+newvias
save_plan('usb-short-routing-v13',failed)
(P/'manifests/usb-short-reroute-nets-v13.json').write_text(json.dumps(sorted(changed)))
