from pathlib import Path
exec(Path('PCB/scripts/router-v13.py').read_text(encoding='utf-8'))
load_plan(P/'manifests/critical-routing-v13.json')
failed=[]
def pt(r,p):return (*xy(r,p),next(q['layer'] for q in pads if q['ref']==r and q['number']==p))
def connect(r,p,s,q,w=.2,allowed=(1,2,16)):
 a,b=pt(r,p),pt(s,q);net=next(v['net'] for v in pads if v['ref']==r and v['number']==p)
 if not(addline(net,1,[a[:2],b[:2]],w) or addroute(net,a,b,w,allowed)):failed.append([r,p,s,q,net])
# Short top-layer RF feed, local passives and U.FL, target 50 ohm pending factory stack calculation.
connect('U2','35','R50','1',.35,(1,));connect('R50','1','C50','1',.35,(1,));connect('R50','2','J5','2',.35,(1,));connect('J5','2','C51','1',.35,(1,))
# Series resistor to module pads; preserve both signals as an adjacent pair.
for a,b,c,d in [('U1','14','R15','1'),('U1','13','R16','1'),('U2','59','R60','1'),('U2','60','R61','1')]:connect(a,b,c,d,.2,(1,))
# Connector and ESD fanout, grouped before low speed signals.
for a,b,c,d in [('R15','2','D18','1'),('D18','1','J6','2'),('R16','2','D18','2'),('D18','2','J6','3'),('R60','2','D20','1'),('D20','1','J7','2'),('R61','2','D20','2'),('D20','2','J7','3')]:connect(a,b,c,d,.2)
save_plan('interface-routing-v13',failed)
