from pathlib import Path
s=Path('PCB/scripts/plan-interface-routing-v11.py').read_text();exec(s[:s.rindex("d=json.loads")]);net='232_VPLUS';ps=[p for p in pads if p['net']==net];a=(ps[0]['x'],ps[0]['y'],0);b=(ps[1]['x'],ps[1]['y'],0);masks=[maskgeom(obstacles(net,k),.1524/2+.18) for k in [1,2,16]];vm=maskgeom(unary_union([obstacles(net,k) for k in [1,2,16]]+[p['geom'].buffer(-.19) for p in pads if p['net']==net and p['layer']==1]+[Point(v['x'],v['y']).buffer(v['diameter']/2) for v in vias]),.225+.18);seq=findroute(a,b,net,masks,vm);print(a,b,'seq',None if seq is None else len(seq),'valid',False if seq is None else valid(a,b,seq,net));print('masked',masks[0][round(a[1]/step),round(a[0]/step)],masks[0][round(b[1]/step),round(b[0]/step)])



print([(u[0]*step,u[1]*step,u[2],v[2],round(Point(u[0]*step,u[1]*step).distance(unary_union([p['geom'] for p in pads if p['net']==net and p['layer']==1])),3)) for u,v in zip(seq,seq[1:]) if u[2]!=v[2]])
