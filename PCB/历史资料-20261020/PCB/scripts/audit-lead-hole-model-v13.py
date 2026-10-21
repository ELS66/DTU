from pathlib import Path
import json,zipfile
exec(Path('PCB/scripts/router-v13.py').read_text(encoding='utf8').replace('read-pcb-pads-v13.json','silkclean-pcb-pads-v13.json'))
code=Path('PCB/scripts/package-silkclean-v13.py').read_text(encoding='utf8');exec(code[code.index('def active_project('):code.index('oldproj=active_project(')])
a=active_project(Path('PCB/eda/DTU-V0.13-60x70-Silkholefix.epro2'));plan=json.loads((P/'manifests/exposure-fixed-actual-routing-v13.json').read_text(encoding='utf8'));out=[];lead_geoms=[]
for ref in ['Q1','J4']:
 c=by[ref]
 for k,r in a.items():
  if k[0]!='FOOTPRINT' or k[1]!=c['footprint']['uuid'] or not isinstance(r,dict) or r.get('layerId') not in [50,51] or 'path' not in r:continue
  ps=r['path'];ps=ps if isinstance(ps[0],list) else [ps]
  for path in ps:
   v=[x*.0254 for x in path if isinstance(x,(int,float))];g=Polygon(list(zip(v[::2],v[1::2]))).buffer(0);g=translate(rotate(g,c['rotation'],origin=(0,0)),c['x']*.0254,c['y']*.0254);lead_geoms.append({'ref':ref,'id':k[-1],'layer':r['layerId'],'geom':g})
   for via in plan['vias']:
    gap=g.distance(Point(via['x'],via['y']).buffer(via['hole']/2))
    if gap<.25:out.append({'ref':ref,'leadGeometryId':k[-1],'modelLayer':r['layerId'],'leadBoundsMm':list(g.bounds),'via':via,'gapMm':gap})
if __name__=='__main__':
 print(json.dumps(out,indent=2));(P/'manifests/lead-hole-model-pairs-v13.json').write_text(json.dumps(out,indent=2))

