exec(open('PCB/scripts/plan-usb-core-v07.py',encoding='utf-8-sig').read().split('for label,nets,layer,ends')[0])
a=(44,35.2);b=(50.945,34.5);ln=LineString([a,b]).buffer(.28)
for t in tracks:
 if t['layer']==1 and t['net']!='LTE_USB_DP' and t['geom'].intersects(ln):print('blocker',t['net'],t['geom'].bounds)
obs=obstacles('LTE_USB_DP',1);print('dist endpoints',Point(*a).distance(obs),Point(*b).distance(obs))
for p in pads:
 if p['geom'].distance(Point(*a))<.4 and p['net']!='LTE_USB_DP':print('nearby',p['ref'],p['number'],p['net'],p['geom'].bounds)
