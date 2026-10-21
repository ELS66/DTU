from pathlib import Path
import zipfile,json,math,sys
sys.path.insert(0,str(Path('PCB/.tools').resolve()))
from shapely.geometry import Polygon,Point,box
from shapely.affinity import rotate,translate
from shapely.ops import unary_union
from shapely.strtree import STRtree
P=Path('PCB');cs=json.load(open(P/'manifests/read-pcb-pads-v13.json',encoding='utf-8'))['result'];by={c['ref']:c for c in cs};fps={};current=None
with zipfile.ZipFile(P/'eda/DTU-V0.13-55x65-accepted-reduction.epro2') as z:s=z.read(next(n for n in z.namelist() if n.endswith('.epru'))).decode('utf-8')
for l in s.splitlines():
 if '||' not in l:continue
 h,b=l.split('||',1);h=json.loads(h);b=json.loads(b.rstrip('|')) if b.rstrip('|') else {}
 if h['type']=='DOCHEAD':current=b['uuid'] if b.get('docType')=='FOOTPRINT' else None
 elif current:fps.setdefault(current,[]).append({'type':h['type'],**b})
(P/'manifests/footprint-geometries-v13.json').write_text(json.dumps(fps),encoding='utf-8');base={};body={}
for c in cs:
 gs=[];bs=[]
 for b in fps[c['footprint']['uuid']]:
  if b['type']=='POLY' and b.get('layerId')==48:
   a=[v*.0254 for v in b['path'] if isinstance(v,(int,float))]
   if len(a)>=6:bs.append(Polygon(list(zip(a[::2],a[1::2]))).buffer(0))
 for p in c['pads']:
  x,y=p['x']*.0254,p['y']*.0254
  if p['shape'][0]=='POLYGON':
   a=[v*.0254 for v in p['shape'][1] if isinstance(v,(int,float))];g=Polygon(list(zip(a[::2],a[1::2])))
  else:
   w,h=[v*.0254 for v in p['shape'][1:3]];g=Point(0,0).buffer(max(w,h)/2) if p['shape'][0]=='ELLIPSE' else box(-w/2,-h/2,w/2,h/2);g=translate(rotate(g,p['rotation'],origin=(0,0)),x,y)
  g=rotate(translate(g,-c['x']*.0254,-c['y']*.0254),-c['rotation'],origin=(0,0));gs.append(g)
 body[c['ref']]=unary_union(bs or gs);base[c['ref']]=unary_union(gs+bs).convex_hull.buffer(.17)
fixed={'U1':(36.4,40.6,0),'U2':(13.6,41.925,90),'J7':(16.6,55.5,0),'J6':(35.6,55.5,0),'J5':(9.5,51.5,180),'J1':(12.7,3.3,180),'J2':(25,3.3,180),'J3':(37.3,3.3,180),'J4':(10.5,17.8,-90),'D30':(48.6,43,90),'D31':(48.6,38.5,90),'D32':(48.6,34,90),'D33':(1.4,43,90),'D34':(1.4,38.5,90),'D35':(1.4,34,90),'D36':(33.5,24.9,0),'D37':(42,24.9,0),'C80':(8.5,29.8,0),'C85':(18.3,29.8,0),'L1':(23.5,20.5,180),'U4':(30,20.5,0),'U5':(39,17,-90),'L2':(44,17,0),'U6':(10.7,8.2,90),'U7':(25,9,0),'F1':(42,8.4,90),'D1':(17.5,7.5,90),'D2':(32,7.8,90),'D3':(46,22.3,0),'D4':(34.5,13.8,0)}
prefs={'C90':(31.2,24,90),'C91':(32.7,21.8,90),'C92':(29.5,17.9,0),'C93':(21,25.5,0),'C94':(18,18,90),'R90':(32.8,19.5,180),'R91':(32.8,18.2,0),'C95':(33.75,16.8,0),'C96':(36.45,18.5,90),'C97':(40.5,19.5,0),'C98':(47.1,18.1,90),'C99':(47.1,14.4,90),'C106':(39,13.9,0),'C1':(36,11.6,90),'C2':(39,11.1,0),'R15':(25,29.124,180),'R16':(25,30.394,180),'R60':(18.398,49.0,90),'R61':(17.2,49.0,90),'D18':(34.3,53.1,0),'D20':(15.3,53.1,0),'R50':(7.0,48.9,90),'C50':(4.0,49.8,90),'C51':(11.5,49.0,0),'D10':(12.0,51.5,0),'RN1':(45,28,90),'RN2':(3.2,29,90),'RN3':(46.5,30,90),'RN4':(24,34,90),'RN5':(19,14,0),'U10':(24.8,37,0),'U12':(30,13,0)}
fixed={r:(x+2.5,y+2.5,a) for r,(x,y,a) in fixed.items()}
fixed['U1']=(38.9,43.325,270)
for r in ['D30','D31','D32']:fixed[r]=(53.6,fixed[r][1],90)
for r in ['D33','D34','D35']:fixed[r]=(1.4,fixed[r][1],90)
prefs={r:(x+2.5,y+2.5,a) for r,(x,y,a) in prefs.items()}
prefs['U10']=(27,31,0)
prefs['R15']=(30.326,54,90)
prefs['R16']=(31.596,54,90)
prefs['C10']=(43.6,54,90)
prefs['C11']=(45.3,54,90)
prefs['C70']=(29,31,90)
prefs['C71']=(25,31,90)
prefs['RN4']=(25,32,0)
fixed['U7']=(27.5,12.25,180)
fixed['J4']=(14,21.3,-90)
fixed['U6']=(13.2,11.2,90)
for r in ['J1','J2','J3']:fixed[r]=(fixed[r][0],3.3,180)
fixed['U1']=(39.3,43.325,270)
fixed['U2']=(15.3,44.425,90)
fixed['C80']=(11,30.2,0)
fixed['C85']=(20.8,30.2,0)

prefs={**{'C30':(29.125,16.9,0),'C31':(27,18.1,0),'C32':(29.25,18.4,0),'C33':(25.2,16.8,0),'C34':(31.5,9.6,90),'C35':(31.5,11.3,90),'C38':(32,18,0)},**prefs}

fixed={r:t for r,t in fixed.items() if r in by}
prefs={r:t for r,t in prefs.items() if r in by}
fixed['U5']=(43,21,0)
prefs.update({'C106':(45.1,21,90),'C98':(40.9,21,90),'R94':(42.35,18.6,90),'R95':(43.8,18.6,90),'Q1':(30.5,32,0)})
fixed={r:(x+2.5,y+4,a) for r,(x,y,a) in fixed.items()}
prefs={r:(x+2.5,y+4,a) for r,(x,y,a) in prefs.items()}
fixed.update({'U1':(41.8,48.325,270),'U2':(17.8,49.425,90),'J7':(21.6,63,0),'J6':(40.6,63,0),'J5':(14,59.5,180),'C80':(13.5,36.5,0),'C85':(23.3,36.5,0),'J4':(15,24,-90),'L1':(29.25,27.5,180),'U4':(36.25,27.5,0),'U5':(47.5,25,0)})
for r,x in [('J1',16.5),('J2',30),('J3',43.5)]:fixed[r]=(x,3.3,180)
for refs,x in [(['D30','D31','D32'],58.6),(['D33','D34','D35'],1.4)]:
 for ref,y in zip(refs,[50.5,46,41.5]):fixed[ref]=(x,y,90)
prefs.update({'C90':(35.8,31.5,90),'C91':(38.9,28.1,90),'C92':(35.05,24.9,0),'R90':(38.8,25.25,180),'R91':(38.8,23.8,0),'C95':(39.8,22.1,0),'C106':(49.75,25,270),'C98':(47,28.5,0),'R94':(44.7,24,90),'R95':(43.1,24,270),'Q1':(33,37,0),'U10':(35.8,37,0),'C70':(38.5,37,90),'C71':(30.5,37,90),'RN4':(32.5,34.5,0),'RN5':(23,23,90)})
rev=json.load(open(P/'manifests/revision-v13.json',encoding='utf-8'));forbidden=unary_union([Point(x,y).buffer(3.4) for x,y in [(4,4),(56,4),(4,66),(56,66)]]);board=box(.1,.1,59.9,69.9);placed={};geoms=[]
def geom(ref,x,y,r):return translate(rotate(base[ref],r,origin=(0,0)),x,y)
tree=None
def fits(g):return board.covers(g) and not g.intersects(forbidden) and (tree is None or len(tree.query(g,predicate='intersects'))==0)
def put(ref,target,limit=6,rots=None):
 global tree
 tx,ty,tr=target;opts=[]
 for rr in rots or [tr]:
  for dx in range(-int(limit*4),int(limit*4)+1):
   for dy in range(-int(limit*4),int(limit*4)+1):
    x,y=tx+dx*.25,ty+dy*.25;dist=dx*dx+dy*dy
    opts.append((dist,rr!=tr,x,y,rr))
 for _,_,x,y,r in sorted(opts):
  g=geom(ref,x,y,r)
  if fits(g) and (ref in ['J1','J2','J3'] or g.bounds[1]>=8.5):placed[ref]=(x,y,r);geoms.append(g);tree=STRtree(geoms);return True
 return False
for ref,t in fixed.items():
 if not put(ref,t,0 if ref in ['U1','U2','J1','J2','J3','J6','J7'] or ref.startswith('D3') else 4):
  g=geom(ref,*t);print('Placed so far',placed);print('DEBUG',ref,base[ref].bounds,g.bounds,'intersections',[(r,round(g.intersection(q).area,3)) for r,q in zip(placed,geoms) if g.intersects(q)],'hole',g.intersects(forbidden),'edge',board.covers(g));raise Exception('Fixed blocked '+ref)
for ref,t in prefs.items():
 if not put(ref,t,4):print('PREF deferred',ref)
anchors={1:(36,9),2:(46,29),3:(4,32),4:(18,16),5:(27,10),6:(30,13),7:(25,34),8:(33,18),9:(5,29)}
remaining=sorted([c for c in cs if c['ref'] not in placed],key=lambda c:-base[c['ref']].area)
for c in remaining:
 r=c['ref'];tx,ty=tuple(z+5 for z in anchors[rev['componentPages'][r]])
 if not put(r,(tx,ty,c['rotation']),24,[c['rotation'],(c['rotation']+90)%360]):raise Exception('No space '+r)
print('PACKED',len(placed),'bounds',unary_union(geoms).bounds,'fixed shift',[(r,placed[r]) for r in fixed if placed[r]!=fixed[r]])
rows=[{'ref':r,'xMm':x,'yMm':y,'rotation':a,'layer':1} for r,(x,y,a) in placed.items()];(P/'manifests/placement-v13.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
guard="if((await eda.dmt_Project.getCurrentProjectInfo())?.uuid!=='"+rev['projectUuid']+"'||(await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=='4211128ecf040c100b33238447713203')throw Error('Wrong PCB');"
for i in range(0,len(rows),18):
 code=guard+'const rows='+json.dumps(rows[i:i+18])+";const cs=await eda.pcb_PrimitiveComponent.getAll();for(const z of rows){const c=cs.find(c=>c.getState_Designator()===z.ref);if(!c||!await eda.pcb_PrimitiveComponent.modify(c,{layer:1,x:z.xMm/.0254,y:z.yMm/.0254,rotation:z.rotation}))throw Error('Placement '+z.ref);}return {saved:await eda.pcb_Document.save()};";(P/f'scripts/apply-placement-v13-{i//18+1}.js').write_text(code,encoding='utf-8')


