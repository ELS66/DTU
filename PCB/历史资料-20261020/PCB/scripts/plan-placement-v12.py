"""Build an independently checked 50x60 mm component placement; never replay V0.11."""
import json,math,sys,random
from pathlib import Path
sys.path.insert(0,str(Path('PCB/.tools').resolve()))
from shapely.geometry import box,Point,Polygon
from shapely.affinity import rotate,translate,scale
P=Path('PCB');cs=json.load(open(P/'manifests/pcb-pads-stage-v12.json',encoding='utf-8'))['result'];by={c['ref']:c for c in cs};fps=json.load(open(P/'manifests/footprint-geometries-v12.json',encoding='utf-8'))
plan={};placed={};holes=[Point(x,y).buffer(3.4) for x,y in [(4,4),(46,4),(4,56),(46,56)]]
def shape(r,rot,layer):
 c=by[r];b=c['bbox'];g=box((b['minX']-c['x'])*.0254,(b['minY']-c['y'])*.0254,(b['maxX']-c['x'])*.0254,(b['maxY']-c['y'])*.0254)
 g=rotate(g,-c['rotation'],origin=(0,0));g=rotate(g,rot,origin=(0,0))
 return scale(g,xfact=-1,origin=(0,0)) if layer==2 else g
def put(r,x,y,rot=0,layer=1):
 plan[r]={'x':x,'y':y,'rotation':rot,'layer':layer};placed[r]=translate(shape(r,rot,layer),x,y)
macro={'U1':(35.65,41.975,0),'U2':(14.2,37.9,90),'J7':(18,56,0),'J6':(34,56,0),'J5':(7.6,51.5,180),'J4':(10,15.0,-90),'J1':(12.7,3.3,180),'J2':(25,3.3,180),'J3':(37.3,3.3,180),'C80':(32,23.0,90),'C85':(32,14.2,90),'L1':(22.5,23.5,0),'U4':(22.5,16.3,0),'U5':(38.5,24,-90),'L2':(44.5,24,0),'U11':(39.2,14.7,-90),'L3':(45.3,15.0,0),'U7':(25,9,180),'U8':(39.8,9,0),'D36':(38.5,19.2,0),'D37':(45,19.2,0)}
for r,pos in macro.items():put(r,*pos)
for i in range(3):
 put('D'+str(33+i),1.8,43.6-5.3*i,90);put('D'+str(30+i),48.2,43.6-5.3*i,90)
for r,x,y,rot in [('SW2',32,27,0),('SW3',41.5,27,0),('SW4',22,13,0),('U6',10,10.3,-90),('U3',9,6,0),('U12',35,13.5,90),('U10',26,36,0),('U13',26,40,0)]:put(r,x,y,rot,2)
def ok(r,g,layer,gap=.28):
 if not box(.5,.5,49.5,59.5).covers(g) or any(g.intersects(h) for h in holes):return False
 for other,q in placed.items():
  if other==r or plan[other]['layer']!=layer:continue
  if g.distance(q)<gap:return False
 return True
def anchor(r):
 n=int(''.join(x for x in r if x.isdigit()));p=r.rstrip('0123456789')
 if r in ['R140','R141','R142']:return (46.4,43.6-5.3*(n-140))
 if r in ['R143','R144','R145']:return (3.6,43.6-5.3*(n-143))
 if r in ['R146','R147']:return (32.5 if n==146 else 41.6,17.5)
 if p in ['C','R','D'] and n in range(90,96):return (23.5,18.5)
 if p=='C' and n in range(96,100):return (40,25)
 if p=='C' and n in range(106,110) or r in ['R92','R93','D14']:return (40,15)
 if p in ['C','R','D'] and n in range(50,58):return (19,31)
 if p in ['C','R','D'] and n in range(60,86) or r in ['Q1','Q2']:return (25,36)
 if p in ['C','R','D'] and n in range(10,22):return (35,42)
 if p in ['C','R','D','F'] and n<10:return (14,6)
 if r in ['R100','R101','C35','R30']:return (9,11)
 if p=='C' and n in range(30,35):return (25,10)
 if r in ['C36','C37','C38','R31','R32','R33','R34','R35','R36','R121']:return (40,9)
 if r in ['R37','R38']:return (35,13.5)
 return (25,20)
toprefs=['C90','C91','C92','C93','C94','C95','R90','R91','C96','C97','C98','C99','C106','C107','C108','C109','R92','R93','D14','R50','D10','C50','C51']
done=set(plan)
for r in sorted([c['ref'] for c in cs if c['ref'] not in done],key=lambda r:-shape(r,0,1).area):
 layer=1 if r in toprefs else 2;target=anchor(r)
 if r in ['R50','D10','C50','C51']:target=(9.3,50)
 nets={p['net'] for p in by[r]['pads'] if p['net'] not in ['','GND','VIN_PROTECTED','VIN_RAW','VDD_3V3','VDD_4G','LTE_VDD_EXT','VDD_TTL_5V']}
 neighbours=[q for q in plan if nets.intersection(p['net'] for p in by[q]['pads'])]
 candidates=[]
 for rot in [0,90,180,270]:
  g=shape(r,rot,layer)
  for dx in range(2,99):
   for dy in range(2,119):
    x=dx*.5;y=dy*.5;distance=math.dist((x,y),target)
    if distance>60:continue
    cost=distance+sum(.12*math.dist((x,y),(plan[q]['x'],plan[q]['y'])) for q in neighbours)
    candidates.append((cost,x,y,rot))
 candidates.sort()
 for cost,x,y,rot in candidates:
  g=translate(shape(r,rot,layer),x,y)
  if ok(r,g,layer):put(r,x,y,rot,layer);break
 else:raise RuntimeError('No space '+r)
conflicts=[]
for i,r in enumerate(plan):
 for q in list(plan)[:i]:
  if plan[r]['layer']==plan[q]['layer'] and placed[r].distance(placed[q])<.18:conflicts.append((r,q,round(placed[r].distance(placed[q]),3)))
print('Placement',len(plan),'top',sum(p['layer']==1 for p in plan.values()),'conflicts',conflicts)
(P/'manifests/placement-v12.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
guard="if((await eda.dmt_Project.getCurrentProjectInfo())?.uuid!=='be907e0c26ece4ccdedd2f5b24e25f76812bc6b957961675838d5450e3220cbc'||(await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=='4211128ecf040c100b33238447713203')throw Error('Wrong PCB');"
enum='const EPCB_LayerId={TOP:1,BOTTOM:2,BOARD_OUTLINE:11,MULTI:12};'
for k in range(0,len(plan),35):
 items={r:{**p,'id':by[r]['id']} for r,p in list(plan.items())[k:k+35]}
 code=guard+enum+'const map='+json.dumps(items)+";for(const [r,s] of Object.entries(map)){const c=await eda.pcb_PrimitiveComponent.get(s.id);const a=c.toAsync();a.setState_Layer(s.layer===1?EPCB_LayerId.TOP:EPCB_LayerId.BOTTOM);a.setState_Rotation(s.rotation);a.setState_X(s.x/.0254);a.setState_Y(s.y/.0254);await a.done();}return {saved:await eda.pcb_Document.save(),count:Object.keys(map).length};"
 (P/f'scripts/apply-placement-v12-{k//35+1}.js').write_text(code,encoding='utf-8')
