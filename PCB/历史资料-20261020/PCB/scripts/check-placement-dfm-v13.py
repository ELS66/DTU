from pathlib import Path
exec(Path('PCB/scripts/router-v13.py').read_text(encoding='utf8'))
from shapely.strtree import STRtree
tr=STRtree([p['geom'] for p in pads]);viol=[]
for i,p in enumerate(pads):
 for j in tr.query(p['geom'].buffer(.149)):
  q=pads[j]
  if j>=i or (p['layer']!=q['layer'] and 12 not in [p['layer'],q['layer']]) or (p['net'] and p['net']==q['net']):continue
  d=p['geom'].distance(q['geom'])
  if d<.149:viol.append([p['ref']+':'+p['number'],q['ref']+':'+q['number'],round(d,4)])
print('Copper pad clearance <0.149mm:',viol)
report={'scope':'placement pads only, routing/DFM not complete','padClearanceThresholdMm':.149,'padClearanceViolations':viol,'componentCount':len(cs),'allTop':all(c['layer']==1 for c in cs),'minimumPadToEdgeMm':min(min(p['geom'].bounds[0],p['geom'].bounds[1],60-p['geom'].bounds[2],70-p['geom'].bounds[3]) for p in pads)}
(P/'manifests/dfm-placement-v13.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(report)
