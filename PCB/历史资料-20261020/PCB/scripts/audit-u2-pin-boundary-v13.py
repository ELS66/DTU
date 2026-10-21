from pathlib import Path
import json,collections,math
exec(Path('PCB/scripts/audit-lead-hole-model-v13.py').read_text(encoding='utf-8-sig').split('for ref in')[0])
c=by['U2'];lib=[(k,r) for k,r in a.items() if k[0]=='FOOTPRINT' and k[1]==c['footprint']['uuid'] and isinstance(r,dict)];padlist=[];leads=[]
for k,r in lib:
 if k[2]=='PAD':
  d=r['defaultPad'];g=rotate(box(-d['width']*.0254/2,-d['height']*.0254/2,d['width']*.0254/2,d['height']*.0254/2),r['padAngle'],origin=(0,0));g=translate(g,r['centerX']*.0254,r['centerY']*.0254);padlist.append({'id':k[-1],'number':r['num'],'geom':g,'raw':r})
 if r.get('layerId')==50 and 'path' in r:
  ps=r['path'];ps=ps if isinstance(ps[0],list) else [ps]
  for p in ps:
   v=[x*.0254 for x in p if isinstance(x,(int,float))];g=Polygon(list(zip(v[::2],v[1::2]))).buffer(0);leads.append({'id':k[-1],'geom':g})
rows=[]
for lead in leads:
 g=lead['geom'];p=min(padlist,key=lambda p:g.centroid.distance(p['geom'].centroid));b=p['geom'];overflow=max([Point(x,y).distance(b) for x,y in g.exterior.coords]);rows.append({'pin':p['number'],'padId':p['id'],'modelId':lead['id'],'padBoundsMm':list(b.bounds),'modelBoundsMm':list(g.bounds),'modelOutsidePadAreaMm2':g.difference(b).area,'maxModelOverhangMm':overflow})
print('pads',len(padlist),'models',len(leads),'notcovered exact',sum(r['modelOutsidePadAreaMm2']>0 for r in rows),'over1um',sum(r['maxModelOverhangMm']>.001 for r in rows),'max',max(r['maxModelOverhangMm'] for r in rows));print('outer example',[r for r in rows if r['pin']=='1']);print('inner',[r for r in rows if r['pin']=='45']);print('sizes',collections.Counter((round(p['raw']['defaultPad']['width']*.0254,3),round(p['raw']['defaultPad']['height']*.0254,3)) for p in padlist))
Path('PCB/manifests/u2-pin-boundary-library-audit-v13.json').write_text(json.dumps({'footprint':c['footprint'],'pinModelCount':len(leads),'padCount':len(padlist),'modelNotCoveredExactCount':sum(r['modelOutsidePadAreaMm2']>0 for r in rows),'modelOverhangAbove1umCount':sum(r['maxModelOverhangMm']>.001 for r in rows),'rows':rows},indent=2))
