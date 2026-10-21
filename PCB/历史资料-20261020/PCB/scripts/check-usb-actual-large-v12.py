from pathlib import Path
script=Path('PCB/scripts/check-usb-lengths-large-v12.py').read_text(encoding='utf-8')
script=script.replace("plan=json.load(open(P/'manifests/critical-large-v12.json'));rows=[]", """native=json.load(open(P/'manifests/routing-signals-complete-large-v12.json'))['result'];plan={'routes':[],'vias':[]};rows=[]
for z in native['polys']:
 if 'USB' not in (z['net'] or ''):continue
 a=z['polygon'];pts=[(a[0]*.0254,a[1]*.0254)]+[(a[i]*.0254,a[i+1]*.0254) for i in range(3,len(a),2)]
 plan['routes'].append({'net':z['net'],'layer':z['layer'],'pointsMm':pts})
for v in native['vias']:
 if 'USB' in v['net']:plan['vias'].append({'net':v['net'],'x':v['x']*.0254,'y':v['y']*.0254})""")
exec(script)
