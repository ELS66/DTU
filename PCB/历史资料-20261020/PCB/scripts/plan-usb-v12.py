from pathlib import Path
exec(Path('PCB/scripts/router-v12.py').read_text(encoding='utf-8'))
load_plan(P/'manifests/rf-routing-v12.json')
s=(P/'scripts/plan-usb-core-v07.py').read_text();exec(s[s.index('def path('):s.index('for label,nets,layer,ends')])
failed=[];cores={};transitions={};lengths={}
def coupled(label,nets,layer,ends):
 obs=obstacles(nets[0],layer,ignore=nets)
 center=LineString({'ESP':[(24.6,35.6),(24.6,49.4),(29.55,54.35),(32.73,54.35)],'LTE':[(16.73,48.25),(16.73,54.35)],'LTE_LOCAL':[(17.8,43.7),(17.8,45.33),(16.73,46.4)]}[label])
 if center is None:raise Exception('No USB pair corridor '+label)
 curves=[center.offset_curve(.2,join_style=2),center.offset_curve(-.2,join_style=2)]
 if any(q.geom_type!='LineString' for q in curves) or curves[0].distance(curves[1])<.397:raise Exception('USB offset invalid '+label)
 for net,g in zip(nets,curves):
  if g.distance(obs)<.12+.158:raise Exception('USB copper clearance '+label)
  if not addline(net,layer,list(g.coords),.24):raise Exception('Pair creation geometry '+net)
 cores[label]={'nets':nets,'layer':layer,'tracks':[list(q.coords) for q in curves],'lengths':[q.length for q in curves]}
 print('coupled',label,cores[label]['lengths'],flush=True)
coupled('ESP',['ESP_USB_DP_EXT','ESP_USB_DM_EXT'],1,[(24.6,35.6),(32.73,54.35)])
coupled('LTE',['LTE_USB_DP_EXT','LTE_USB_DM_EXT'],1,[(16.73,48.25),(16.73,54.35)])
coupled('LTE_LOCAL',['LTE_USB_DP_EXT','LTE_USB_DM_EXT'],2,[(17.8,43.7),(16.73,46.4)])
def connect(net,a,b,width=.2032,allowed=(1,2)):
 if not addroute(net,a,b,width,allowed):failed.append([net,a,b]);print('FAILED',net,a,b,flush=True)
def point(ref,pn):
 q=next(p for p in pads if p['ref']==ref and p['number']==pn);return(q['x'],q['y'],q['layer'])
for net,ref,pn,res in [('ESP_USB_DP','U1','14','R15'),('ESP_USB_DM','U1','13','R16'),('LTE_USB_DP','U2','59','R60'),('LTE_USB_DM','U2','60','R61')]:
 a=point(ref,pn);b=point(res,'1');v=addvia(net,b[:2],source=a[:2],source_layer=1,width=.2032)
 if v is None:raise Exception('No module USB via '+net)
 connect(net,(*v,2),b);print('USB module fanout',net,v,flush=True)
for k,(net,res) in enumerate(zip(cores['ESP']['nets'],['R15','R16'])):
 a=point(res,'2');target=[(24.5,33.9),(24.8,34.9)][k];v=addvia(net,target)
 if v is None:raise Exception('No ESP output USB via')
 connect(net,a,(*v,2));connect(net,(*v,1),(*cores['ESP']['tracks'][k][0],1),.24,(1,))
 connect(net,(*cores['ESP']['tracks'][k][-1],1),point('J6',str(k+2)),.24,(1,));connect(net,point(['D18','D19'][k],'1'),point('J6',str(k+2)),.2032)
for k,(net,res) in enumerate(zip(cores['LTE']['nets'],['R60','R61'])):
 connect(net,point(res,'2'),(*cores['LTE_LOCAL']['tracks'][k][0],2),.24,(2,))
 v=addvia(net,[(16.1,47.1),(17.4,47.1)][k])
 if v is None:raise Exception('No LTE output USB via')
 connect(net,(*cores['LTE_LOCAL']['tracks'][k][-1],2),(*v,2),.24,(2,));connect(net,(*v,1),(*cores['LTE']['tracks'][k][0],1),.24,(1,))
 connect(net,(*cores['LTE']['tracks'][k][-1],1),point('J7',str(k+2)),.24,(1,));connect(net,point(['D20','D21'][k],'1'),point('J7',str(k+2)),.2032)
save_plan('usb-routing-v12',failed)
(P/'manifests/usb-pairs-v12.json').write_text(json.dumps(cores,indent=2),encoding='utf-8')
