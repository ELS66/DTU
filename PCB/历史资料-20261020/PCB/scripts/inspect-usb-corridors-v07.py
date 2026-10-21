exec(open('PCB/scripts/plan-usb-core-v07.py',encoding='utf-8-sig').read().split('for label,nets,layer,ends')[0])
for label,layer,pts in [('ESP',2,[(1.2,43),(1.2,61),(3.6,63.4),(11.5,63.4)]),('LTE',1,[(54.4,35.4),(59,35.4),(59,68.6),(39.9,68.6)])]:
 geom=LineString(pts).buffer(.51);print(label)
 print('tracks',[(t['net'],tuple(round(v,2) for v in t['geom'].bounds)) for t in tracks if t['layer']==layer and t['geom'].intersects(geom)])
 print('vias',[v for v in vias if Point(v['x'],v['y']).buffer(v['diameter']/2).intersects(geom)])
 print('pads',[(p['ref'],p['number'],p['net']) for p in pads if p['layer'] in [layer,12] and p['geom'].intersects(geom)])
