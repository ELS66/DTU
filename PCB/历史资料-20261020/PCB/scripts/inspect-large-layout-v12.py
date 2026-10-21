import json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path('PCB/.tools').resolve()))
from shapely.geometry import Polygon,box,Point
from shapely.affinity import rotate,translate,scale
from shapely.ops import unary_union
from PIL import Image,ImageDraw,ImageFont
P=Path('PCB');cs=json.load(open(P/'manifests/pcb-pads-enlarged-v12.json',encoding='utf8'))['result'];by={c['ref']:c for c in cs};fps=json.load(open(P/'manifests/footprint-geometries-v12.json',encoding='utf8'));body={}
for c in cs:
 out=[]
 for b in fps[c['footprint']['uuid']]:
  if b['type']=='POLY' and b.get('layerId')==48:
   nums=[z*.0254 for z in b['path'] if isinstance(z,(int,float))]
   if len(nums)<6:continue
   g=Polygon(list(zip(nums[::2],nums[1::2]))).buffer(0)
   if c['layer']==2:g=scale(g,xfact=-1,origin=(0,0))
   out.append(translate(rotate(g,c['rotation'],origin=(0,0)),c['x']*.0254,c['y']*.0254))
 if not out:
  pp=[(q['x']*.0254,q['y']*.0254) for q in c['pads']];out=[Polygon(pp).convex_hull.buffer(.25)] if len(pp)>2 else [Point(c['x']*.0254,c['y']*.0254).buffer(.5)]
 body[c['ref']]=unary_union(out)
bad=[]
for i,a in enumerate(cs):
 for b in cs[:i]:
  if a['layer']==b['layer'] and body[a['ref']].intersection(body[b['ref']]).area>.01:bad.append([a['ref'],b['ref'],round(body[a['ref']].intersection(body[b['ref']]).area,3)])
print('body overlaps',bad)
for r in ['U1','U2','J4','J1','J2','J3']:print(r,body[r].bounds)
for side in [1,2]:
 im=Image.new('RGB',(1300,1570),'#f5f6f7');d=ImageDraw.Draw(im);f=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18);big=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',26);cn=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',25)
 def xy(x,y):return (50+x*20,1450-y*20)
 d.rectangle([xy(0,70),xy(60,0)],fill='#132726',outline='#c4c9c8',width=3)
 for x,y in [(4,4),(56,4),(4,66),(56,66)]:
  x,y=xy(x,y);d.ellipse((x-68,y-68,x+68,y+68),outline='#516661',width=2);d.ellipse((x-32,y-32,x+32,y+32),fill='#f5f6f7')
 for c in cs:
  if c['layer']!=side:continue
  g=body[c['ref']];a,b,e,h=g.bounds
  color='#a8b2b1' if c['ref'] in ['U1','U2'] else '#415453' if c['ref'].startswith('U') else '#222b2a' if c['ref'].startswith('L') else '#b1ac84' if c['ref'].startswith('J') else '#788787'
  if c['ref'] in ['J6','J7']:d.rectangle([xy(a,h),xy(e,b)],outline='#d8dedb',width=1)
  elif c['ref'] in ['C80','C85']:d.ellipse([xy(a,h),xy(e,b)],fill='#acb7b4',outline='#d8dedb',width=2)
  else:d.rectangle([xy(a,h),xy(e,b)],fill=color,outline='#d8dedb',width=1)
  if c['ref'].startswith('D3'):d.ellipse([xy(a,h),xy(e,b)],fill={'D30':'#fc6860','D31':'#6aea99','D32':'#68a0ff','D33':'#fc6860','D34':'#6aea99','D35':'#68a0ff','D36':'#6aea99','D37':'#68a0ff'}.get(c['ref'],color))
  x,y=xy((a+e)/2,(b+h)/2)
  if c['ref'] not in ['J1','J2','J3','J5','J6','J7'] and not c['ref'].startswith('D3'):
   d.text((x,y),{'U1':'ESP32-C5','U2':'ML307R-DL','C80':'220 uF','C85':'220 uF','J4':'SIM'}.get(c['ref'],c['ref']),font=big if c['ref'] in ['U1','U2'] else f,fill='white',anchor='mm')
  for q in c['pads']:
   if q['layer']==12:
    x,y=xy(q['x']*.0254,q['y']*.0254);d.ellipse((x-16,y-16,x+16,y+16),fill='#dfc288');d.ellipse((x-8,y-8,x+8,y+8),fill='#101918')
 if side==1:
  for t in json.load(open(P/'manifests/silk-large-v12.json')):
   if t['text'] in ['ML307R-DL','DTU V0.12'] or t['x'] in [3.8,56.2]:continue
   d.text(xy(t['x'],t['y']),t['text'],font=f,fill='#edf0e8',anchor='mm')
 d.text((50,12),'V0.12 / 60 × 70 mm / '+('正面布局' if side==1 else '背面布局，正面投影'),font=cn,fill='#111')
 d.text((50,1504),'按实际封装坐标绘制的布局示意；四角 Ø3.2 mm，孔距 52 × 62 mm。',font=cn,fill='#263432')
 d.text((50,1540),'底部接口间距 2.00 mm；顶部两组下载裸焊孔间距 2.54 mm。',font=cn,fill='#263432')
 im.save(P/f'eda/DTU-V0.12-placement-{side}.png')
