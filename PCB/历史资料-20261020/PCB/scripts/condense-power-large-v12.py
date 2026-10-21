from pathlib import Path
exec(Path('PCB/scripts/router-large-v12.py').read_text(encoding='utf8'))
a=json.load(open(P/'manifests/power-routing-large-v12.json'));out=[]
for r in a['routes']:
 w=max(v for v in [.127,.1524,.2032,.254,.35,.45,.6,.8,1.2,1.5] if v<=r['widthMm']+.000001);r['widthMm']=w
 if out and all(out[-1][k]==r[k] for k in ['net','layer','widthMm']) and math.dist(out[-1]['pointsMm'][-1],r['pointsMm'][0])<.000001:out[-1]['pointsMm'].extend(r['pointsMm'][1:])
 else:out.append(r)
new.extend(out);newvias.extend(a['vias']);save_plan('power-condensed-large-v12',a['failed'])
