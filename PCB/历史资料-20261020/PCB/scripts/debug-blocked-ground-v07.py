from pathlib import Path
exec(Path('PCB/scripts/repair-routing-core-v07.py').read_text(encoding='utf-8'))
for ref,num in [('U3','8'),('R12','1'),('U1','28')]:
 q=next(q for q in pads if q['ref']==ref and q['number']==num);pt=Point(q['x'],q['y']);obs=obstacles('GND',1);print(ref,num,'distance',pt.distance(obs),'masked',raster('GND',1,.1524)[0][round(q['y']/step),round(q['x']/step)]);print('tracks',[(t['net'],t['layer'],round(pt.distance(t['geom']),4)) for t in sorted([t for t in tracks if t['net']!='GND' and t['layer']==1],key=lambda t:pt.distance(t['geom']))[:3]]);print('vias',[(v['net'],v['x'],v['y'],round(pt.distance(Point(v['x'],v['y']).buffer(.3)),3)) for v in sorted([v for v in vias if v['net']!='GND'],key=lambda v:pt.distance(Point(v['x'],v['y'])))[:3]])
