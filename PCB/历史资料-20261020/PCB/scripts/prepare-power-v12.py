from pathlib import Path
exec(Path('PCB/scripts/router-v12.py').read_text())
p=json.load(open(P/'manifests/power-routing-v12.json'));original=len(p['routes']);out=[];removed=[]
for r in p['routes']:
 if any(LineString(r['pointsMm']).distance(h)<r['widthMm']/2+.153 for h in holes[-2:]):removed.append(r);continue
 w=max([k for k in [.127,.1524,.2032,.254,.35,.45,.6,.8,1.2,1.5] if k<=r['widthMm']+.0001]);r['widthMm']=w
 if out and out[-1]['net']==r['net'] and out[-1]['layer']==r['layer'] and out[-1]['widthMm']==w and math.dist(out[-1]['pointsMm'][-1],r['pointsMm'][0])<.001:out[-1]['pointsMm'].extend(r['pointsMm'][1:])
 else:out.append(r)
new.extend(out);newvias.extend(p['vias']);save_plan('power-ready-v12',p['failed']);print('Condensed',original,'to',len(out),'removed for SIM holes',len(removed))
