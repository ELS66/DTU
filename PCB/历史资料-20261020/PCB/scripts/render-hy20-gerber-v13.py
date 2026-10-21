import sys,re,math,zipfile,json
from pathlib import Path
sys.path.insert(0,str(Path('PCB/.tools').resolve()))
from shapely.geometry import Point,box,LineString,Polygon
from shapely.ops import unary_union
from PIL import Image,ImageDraw,ImageFont
P=Path('PCB');z=zipfile.ZipFile(P/'eda/DTU-V0.13-60x70-HY20-Gerber-raw')
def read(name):
 text=z.read(name).decode('ascii');aps={};out=[];x=y=0;ap=10;reg=False;contours=[];pts=[];dark=True
 for l in text.splitlines():
  l=l.strip()
  if l.startswith('%ADD'):
   m=re.match(r'%ADD(\d+)([^,]+),([^*]+)',l)
   if m:aps[int(m[1])]=(m[2],[float(t) for t in m[3].split('X')])
   continue
  if l.startswith('%LPC'):dark=False;continue
  if l.startswith('%LPD'):dark=True;continue
  if l=='G36*':reg=True;contours=[];pts=[];continue
  if l=='G37*':
   if pts:contours.append(pts)
   polygons=[Polygon(t).buffer(0) for t in contours if len(t)>=3];g=Polygon()
   for t in polygons:g=g.symmetric_difference(t)
   out.append((g,dark));reg=False;pts=[];continue
  m=re.match(r'G54D(\d+)',l)
  if m:ap=int(m[1]);continue
  if not ('X' in l or 'Y' in l) or not l.startswith(('G01','G02','G03','X','Y')):continue
  vals={k:float(v)/1e6 for k,v in re.findall(r'([XYIJ])(-?\d+)',l)};xx=vals.get('X',x);yy=vals.get('Y',y);dm=re.search(r'D0([123])',l)
  if not dm:x,y=xx,yy;continue
  d=int(dm[1]);a,b=aps.get(ap,('C',[.15]));w=b[0];line=[(x,y),(xx,yy)]
  if l.startswith(('G02','G03')):
   cx=x+vals.get('I',0);cy=y+vals.get('J',0);r=math.hypot(x-cx,y-cy);t0=math.atan2(y-cy,x-cx);t1=math.atan2(yy-cy,xx-cx);dt=(t1-t0)%(2*math.pi)
   if l.startswith('G02'):dt=dt-2*math.pi
   n=max(4,int(abs(dt)*r/.03));line=[(cx+r*math.cos(t0+dt*k/n),cy+r*math.sin(t0+dt*k/n)) for k in range(n+1)]
  if reg:
   if d==2:
    if pts:contours.append(pts)
    pts=[(xx,yy)]
   elif d==1:pts+=line[1:]
  elif d==1:out.append((LineString(line).buffer(w/2),dark))
  elif d==3:
   if a=='C':g=Point(xx,yy).buffer(w/2)
   elif a=='R':g=box(xx-b[0]/2,yy-b[1]/2,xx+b[0]/2,yy+b[1]/2)
   elif a=='O':
    r=min(b)/2;g=LineString([(xx-max(0,b[0]-b[1])/2,yy-max(0,b[1]-b[0])/2),(xx+max(0,b[0]-b[1])/2,yy+max(0,b[1]-b[0])/2)]).buffer(r)
   elif a=='RoundRect':
    rr,x1,y1,x2,y2=b;g=box(xx-min(abs(x1),abs(x2)),yy-min(abs(y1),abs(y2)),xx+max(abs(x1),abs(x2)),yy+max(abs(y1),abs(y2))).buffer(rr/2)
   else:raise ValueError(a)
   out.append((g,dark))
  x,y=xx,yy
 return out,aps
cache={}
def geom(name):
 if name not in cache:cache[name]=read(name)
 return cache[name]
def draw_geom(d,g,color,xy):
 if g.is_empty:return
 if g.geom_type=='Polygon':
  d.polygon([xy(*p) for p in g.exterior.coords],fill=color)
  for q in g.interiors:d.polygon([xy(*p) for p in q.coords],fill='#122c29')
 elif hasattr(g,'geoms'):
  for q in g.geoms:draw_geom(d,q,color,xy)
def drill(name):
 t=z.read(name).decode('ascii');tools={int(a):float(b) for a,b in re.findall(r'T(\d+)C([.\d]+)',t)};ap=None;out=[]
 for l in t.splitlines():
  if re.fullmatch(r'T\d+',l):ap=int(l[1:])
  m=re.match(r'X(-?[.\d]+)Y(-?[.\d]+)',l)
  if m:out.append((float(m[1]),float(m[2]),tools[ap]))
 return out
holes=drill('Drill_PTH_Through.DRL')+drill('Drill_NPTH_Through.DRL')
for label,copper,mask,silk in [('top','Gerber_TopLayer.GTL','Gerber_TopSolderMaskLayer.GTS','Gerber_TopSilkscreenLayer.GTO'),('bottom','Gerber_BottomLayer.GBL','Gerber_BottomSolderMaskLayer.GBS','Gerber_BottomSilkscreenLayer.GBO'),('inner1','Gerber_InnerLayer1.G1',None,None),('inner2','Gerber_InnerLayer2.G2',None,None)]:
 im=Image.new('RGB',(1320,1530),'#f5f6f7');d=ImageDraw.Draw(im);xy=lambda x,y:(60+x*20,1450-y*20)
 d.rectangle([xy(0,70),xy(60,0)],fill='#122c29',outline='#889b95',width=2)
 for name,color in [(copper,'#42655a'),(mask,'#d6b775'),(silk,'#f1f2e4')]:
  if name:
   for g,dark in geom(name)[0]:draw_geom(d,g,color if dark else '#122c29',xy)
 for x,y,r in holes:
  px,py=xy(x,y);d.ellipse((px-r*10,py-r*10,px+r*10,py+r*10),fill='#f5f6f7' if r>3 else '#0c1716')
 f=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24);d.text((60,12),f'V0.13 HY2.0 60x70 / exported Gerber / {label} / top-view coordinates',font=f,fill='#152822')
 d.text((60,1480),'Engineering review: assembly, impedance and load-step tests pending.',font=f,fill='#152822')
 im.save(P/f'eda/DTU-V0.13-HY20-Gerber-{label}.png')
print('Rendered exported layers')
