from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text(encoding='utf-8'))
f=json.loads((P/'manifests/power-ground-fanout-v07.json').read_text());vias.extend(f['vias'])
for ref,num in [('U3','8'),('R12','1'),('U1','28'),('U3','6')]:
 q=next(q for q in pads if q['ref']==ref and q['number']==num);pt=Point(q['x'],q['y']);print(ref,num,'source',q['x'],q['y'],'inOwn',q['geom'].covers(pt),'ownBounds',q['geom'].bounds,'near',[(x['ref']+':'+x['number'],x['net'],round(pt.distance(x['geom']),4)) for x in sorted([x for x in pads if x['net']!=q['net']],key=lambda x:pt.distance(x['geom']))[:3]])
