from pathlib import Path
exec(Path('PCB/scripts/router-v12.py').read_text(encoding='utf8'))
for name in ['rf-routing-v12','usb-routing-retained-v12','usb-rework-v12','supply-ground-fanout-v12']:load_plan(P/f'manifests/{name}.json')
fails=[]
for f in json.load(open(P/'manifests/supply-ground-fanout-v12.json'))['failed']:
 q=next(p for p in pads if p['ref']==f['ref'] and p['number']==f['pin']);net=f['net'];targets=sorted([v for v in vias if v['net']==net],key=lambda v:math.dist((q['x'],q['y']),(v['x'],v['y'])))[:10]
 for v in targets:
  if addroute(net,(q['x'],q['y'],q['layer']),(v['x'],v['y'],q['layer']),.1524,(q['layer'],)):
   print('Repaired',f['ref'],f['pin'],net,flush=True);break
 else:fails.append(f)
save_plan('supply-ground-repair-v12',fails)
