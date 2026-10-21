import sys,importlib,math,json
from pathlib import Path
sys.path.insert(0,'PCB/scripts');e=importlib.import_module('eda-v12')
g=Path('PCB/scripts/read-pcb-pads-v12.js').read_text().split('const out=')[0]
code=g+"const Layer={MULTI:12};const Rule={NO_WIRES:5,NO_COMPONENTS:2,NO_FILLS:6,NO_POURS:7};const centers=[[4,4],[46,4],[4,56],[46,56]];const ids=[];for(const [x,y] of centers){const pts=[];for(let i=0;i<=48;i++)pts.push((x+3.4*Math.cos(i*Math.PI/24))/.0254,(y+3.4*Math.sin(i*Math.PI/24))/.0254);const p=await eda.pcb_PrimitiveRegion.create(Layer.MULTI,eda.pcb_MathPolygon.createPolygon([pts[0],pts[1],'L',...pts.slice(2)]),[Rule.NO_WIRES,Rule.NO_COMPONENTS,Rule.NO_FILLS,Rule.NO_POURS],'M3 washer clearance',0,false);if(!p)throw Error('Keepout creation failed');ids.push(p.getState_PrimitiveId());}return {ids};"
e.run(code,'manifests/mounting-keepouts-v12.json');print('Mounting keepouts created',flush=True)
for p in sorted(Path('PCB/scripts').glob('apply-power-ready-v12-*.js'),key=lambda p:int(p.stem.split('-')[-1])):
 r=e.run(p.read_text(),f'manifests/{p.stem}.json');print(p.name,len(r['ids']),flush=True)
