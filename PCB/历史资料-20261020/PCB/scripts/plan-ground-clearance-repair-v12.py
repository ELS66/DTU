from pathlib import Path
exec(Path('PCB/scripts/router-large-v12.py').read_text(encoding='utf-8'))
plan=json.load(open(P/'manifests/ground-planes-final-large-v12.json'));regions=plan['regions'];ids=[]
for f in sorted(P.glob('manifests/apply-ground-planes-final-large-v12-*-result.json'),key=lambda p:int(p.stem.split('-')[-2])):ids.extend(json.load(open(f))['result']['ids'])
assert len(ids)==len(regions);by=dict(zip(ids,regions));drc=json.load(open(P/'manifests/drc-ground-final-large-v12.json'))['result'];bad=set()
for group in drc:
 for sub in group.get('list',[]):
  for e in sub.get('list',[]):bad.update(z for z in e.get('objs',[]) if z in by)
assert bad
mask=unary_union([g.buffer(.02) for g in holes[:4]]+[g.buffer(.16) for g in holes[4:]])
replacements=[]
def emit(q,layer):
 if q.geom_type=='Polygon' and q.area>1e-6:
  assert not q.interiors
  a=[z/.0254 for xy in q.exterior.coords for z in xy];replacements.append({'layer':layer,'poly':[a[0],a[1],'L',*a[2:]]})
 elif hasattr(q,'geoms'):
  for z in q.geoms:emit(z,layer)
for pid in bad:
 r=by[pid];a=r['poly'];pts=[(a[0]*.0254,a[1]*.0254)]+[(a[i]*.0254,a[i+1]*.0254) for i in range(3,len(a),2)];emit(Polygon(pts).difference(mask),r['layer'])
guard=(P/'scripts/read-pcb-pads-v12.js').read_text().split('const out=')[0]
(P/'scripts/delete-clearance-fills-v12.js').write_text(guard+'return {deleted:await eda.pcb_PrimitiveFill.delete('+json.dumps(sorted(bad))+'),saved:await eda.pcb_Document.save()};',encoding='utf-8')
for i in range(0,len(replacements),25):
 code=guard+'const regions='+json.dumps(replacements[i:i+25])+";const ids=[];for(const r of regions){const p=await eda.pcb_PrimitiveFill.create(r.layer,eda.pcb_MathPolygon.createPolygon(r.poly),'GND',0,undefined,false);if(!p)throw Error('Plane failed');ids.push(p.getState_PrimitiveId());}return {ids,saved:await eda.pcb_Document.save()};"
 (P/f'scripts/apply-ground-clearance-repair-v12-{i//25+1}.js').write_text(code,encoding='utf-8')
(P/'manifests/ground-clearance-repair-v12.json').write_text(json.dumps({'deleted':sorted(bad),'replacements':replacements},indent=2),encoding='utf-8')
print('Ground clearance repair',len(bad),'fills to',len(replacements),'fills',flush=True)
