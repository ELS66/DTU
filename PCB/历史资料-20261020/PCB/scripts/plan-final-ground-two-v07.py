from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text().replace('routing-power-v07.json','routing-fixed-signals-v07.json'))
q=next(q for q in pads if q['id']=='27e64738f6dde1f7e91');o=obstacles('GND',1)
for p in pads:
 if p['net']=='GND' and p['id']!=q['id'] and math.dist((q['x'],q['y']),(p['x'],p['y']))<3:
  seg=LineString([(q['x'],q['y']),(p['x'],p['y'])]);print('neighbor',p['ref'],p['number'],round(p['x'],3),round(p['y'],3),'clear',not seg.buffer(.23).intersects(o))
for v in vias:
 if v['net']=='GND' and math.dist((14.83,44.25),(v['x'],v['y']))<3:print('via',v)
