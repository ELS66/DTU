from pathlib import Path
exec(Path('PCB/scripts/router-large-v12.py').read_text(encoding='utf8'))
failed=[];cores={}
def point(r,n):
 q=next(q for q in pads if q['ref']==r and q['number']==n);return q['x'],q['y'],q['layer']
def connect(net,a,b,w=.2032,ls=(1,2)):
 if not addroute(net,a,b,w,ls):failed.append([net,a,b]);print('FAILED',net,a,b,flush=True)
def via(net,pt):
 v=addvia(net,pt)
 if v is None:raise Exception('No critical via '+net+str(pt))
 return v
for net in ['LTE_ANT','LTE_RF_FEED']:
 ps=[p for p in pads if p['net']==net];conn=[ps[0]];rest=ps[1:]
 while rest:
  _,i,j=min((math.dist((a['x'],a['y']),(b['x'],b['y'])),i,j) for i,a in enumerate(conn) for j,b in enumerate(rest));a=conn[i];b=rest.pop(j)
  connect(net,(a['x'],a['y'],1),(b['x'],b['y'],1),.32,(1,));conn.append(b)
 print('RF',net,flush=True)
def pair(name,nets,line):
 g=LineString(line);curves=[g.offset_curve(.2,join_style=2),g.offset_curve(-.2,join_style=2)]
 if any(c.geom_type!='LineString' for c in curves) or curves[0].distance(curves[1])<.397:raise Exception('Invalid coupled pair')
 for n,c in zip(nets,curves):
  if not addline(n,1,list(c.coords),.24):raise Exception('Coupled corridor blocked '+n)
 cores[name]={'nets':nets,'layer':1,'tracks':[list(c.coords) for c in curves],'lengths':[c.length for c in curves]}
pair('ESP',['ESP_USB_DP_EXT','ESP_USB_DM_EXT'],[(28.8,42.5),(28.8,59.4),(32.7,63.3),(38.33,63.3),(38.33,64.0)])
pair('LTE',['LTE_USB_DP_EXT','LTE_USB_DM_EXT'],[(19.13,62.0),(19.13,64.0)])
for net,r,pn,res,target in [('ESP_USB_DP','U1','14','R15',(32.6,39.0)),('ESP_USB_DM','U1','13','R16',(32.6,42.3)),('LTE_USB_DP','U2','59','R60',(22.8,56.1)),('LTE_USB_DM','U2','60','R61',(19.7,56.1))]:
 v=via(net,target);connect(net,point(r,pn),(*v,1));connect(net,(*v,2),point(res,'1'));print('Series',net,v,flush=True)
for k,(net,res,target) in enumerate(zip(cores['ESP']['nets'],['R15','R16'],[(28.6,40),(29.3,41.5)])):
 v=via(net,target);connect(net,point(res,'2'),(*v,2));connect(net,(*v,1),(*cores['ESP']['tracks'][k][0],1),.24,(1,));connect(net,(*cores['ESP']['tracks'][k][-1],1),point('J6',str(k+2)),.24,(1,));connect(net,point(['D18','D19'][k],'1'),point('J6',str(k+2)))
for k,(net,res,target) in enumerate(zip(cores['LTE']['nets'],['R60','R61'],[(18.0,60.5),(20.65,59.35)])):
 v=via(net,target);connect(net,point(res,'2'),(*v,2),.24,(2,));connect(net,(*v,1),(*cores['LTE']['tracks'][k][0],1),.24,(1,));connect(net,(*cores['LTE']['tracks'][k][-1],1),point('J7',str(k+2)),.24,(1,));connect(net,point(['D20','D21'][k],'1'),point('J7',str(k+2)))
save_plan('critical-large-v12',failed);(P/'manifests/usb-pairs-large-v12.json').write_text(json.dumps(cores,indent=2),encoding='utf8')
