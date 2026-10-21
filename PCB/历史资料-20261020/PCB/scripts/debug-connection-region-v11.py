from pathlib import Path
s=Path('PCB/scripts/plan-interface-routing-v11.py').read_text();exec(s[:s.rindex('d=json.loads')]);net='232_RX_RAW';vs=[v for v in vias if v['net']==net];print('vias',vs);a=(vs[0]['x'],vs[0]['y'],2);b=(vs[1]['x'],vs[1]['y'],2);masks=[maskgeom(obstacles(net,k),.0762+.18) for k in [1,2,16]];vm=maskgeom(unary_union([obstacles(net,k) for k in [1,2,16]]+[Point(v['x'],v['y']).buffer(v['diameter']/2) for v in vias]),.225+.18)|maskgeom(unary_union([p['geom'] for p in pads if p['net']==net and p['layer']==1]),.15)
for v in vs:vm[round(v['y']/step),round(v['x']/step)]=False
seq=findroute(a,b,net,masks,vm);print('seq',None if seq is None else len(seq),'valid',False if seq is None else valid(a,b,seq,net))
for p in [a,b]:
 x,y=round(p[0]/step),round(p[1]/step);print(p,'masks',[bool(m[y,x]) for m in masks], 'region', [int(connectivity_roots[int(lab[y,x])+off]) for lab,off in zip(connectivity_labels,connectivity_offsets)])
