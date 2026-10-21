from pathlib import Path
import json
P=Path('PCB');cs=json.loads((P/'manifests/pcb-stage-pads-v04.json').read_text(encoding='utf-8-sig'))['result'];m=json.loads((P/'manifests/full-schematic-netmap.json').read_text(encoding='utf-8'));by={c['ref']:c for c in cs};print('parts',len(cs))
for ref in ['U1','U2','J1','J4','J5','J6','C80','U3','U4','U5','U6','U7','U8','U9','U10','U11','U12','U13','U14']:
 c=by[ref];b=c['bbox'];print(ref,'dimensions mm',round((b['maxX']-b['minX'])*.0254,2),round((b['maxY']-b['minY'])*.0254,2));
 if ref in ['U1','U2','J4','J6']:
  for p in c['pads']:
   if ref=='U2'and p['number']not in ['7','11','12','13','14','17','18','22','23','35','42','43','59','60','100']:continue
   print(' ',p['number'],round((p['x']-c['x'])*.0254,3),round((p['y']-c['y'])*.0254,3))
guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");'
for start in range(0,len(cs),14):
 refs=[c['ref']for c in cs[start:start+14]];maps={r:m[r]for r in refs};code=guard+'const map='+json.dumps(maps)+';let assigned=0;const missing=[];for(const c of await eda.pcb_PrimitiveComponent.getAll()){const r=c.getState_Designator();if(!map[r])continue;const pins=await eda.pcb_PrimitiveComponent.getAllPinsByPrimitiveId(c.getState_PrimitiveId());const nums=new Set(pins.map(p=>p.getState_PadNumber()));for(const n of Object.keys(map[r]))if(!nums.has(n))missing.push(r+":"+n);for(const p of pins){const net=map[r][p.getState_PadNumber()]||"";if(p.getState_Net()!==net){const a=p.toAsync();a.setState_Net(net);await a.done();assigned++;}}}return {assigned,missing,saved:await eda.pcb_Document.save()};';(P/f'scripts/assign-pcb-nets-v04-{start//14+1}.js').write_text(code,encoding='utf-8')
