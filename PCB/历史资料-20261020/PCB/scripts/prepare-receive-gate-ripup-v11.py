import json,sys
from pathlib import Path
s=Path('PCB/scripts/plan-interface-routing-v11.py').read_text();exec(s[:s.rindex('d=json.loads')]);ids=[];n=0
for t in old['lines']:n+=1
for t in old['polys']:
 if t['layer'] not in [1,2,15,16]:continue
 g=tracks[n]['geom'];n+=1
 if t['net']=='GND' and t['layer']==1 and g.distance(Point(46.1,18.65))<.2:ids.append(t['id'])
print('Ground fence',ids);code='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");const ids='+json.dumps(ids)+';if(ids.length&&!await eda.pcb_PrimitivePolyline.delete(ids))throw Error("Ground reroute failed");return {ids,saved:await eda.pcb_Document.save()};';(P/'scripts/open-receive-gate-routing-v11.js').write_text(code)
