from pathlib import Path
exec(Path('PCB/scripts/router-v13.py').read_text(encoding='utf-8'))
for name in ['ground-fanout-v13','remaining-routing-v13']:load_plan(P/f'manifests/{name}.json')

def pt(r,p):return (*xy(r,p),next(q['layer'] for q in pads if q['ref']==r and q['number']==p))
failed=[]
def connect(r,p,s,q,w=.254,allowed=(1,)):
 a,b=pt(r,p),pt(s,q);net=next(v['net'] for v in pads if v['ref']==r and v['number']==p)
 if not(addline(net,1,[a[:2],b[:2]],w) or addroute(net,a,b,w,allowed)):failed.append([r,p,s,q,net])
# Local regulator switch, bootstrap and input loops, no layer change.
for a,b,c,d,w in [('U4','5','L1','1',.65),('U4','6','C92','1',.2),('U4','5','C92','2',.3),('U4','3','C91','1',.55),('C91','1','C90','1',.8),('U4','2','U4','3',.35),('U4','1','R90','2',.2),('R90','2','R91','1',.2),('R90','2','C95','2',.2),('U5','4','U5','6',.254),('U5','6','C106','1',.3),('U5','1','C98','1',.35),('U5','2','R94','2',.2),('R94','2','R95','1',.2),('U5','1','R94','1',.2)]:connect(a,b,c,d,w)
for a,b,c,d,w in [('L1','2','C93','1',.8),('L1','2','C94','1',.8),('C93','1','C80','1',.8),('C80','1','C85','1',.8),('C80','1','U2','42',.8),('C80','1','U2','43',.6),('C93','1','U5','6',.4),('C98','1','U1','2',.6),('F1','2','C90','1',.8)]:connect(a,b,c,d,w,(1,2,16))
save_plan('critical-routing-v13',failed)
