from pathlib import Path
exec(Path('PCB/scripts/repair-routing-core-v07.py').read_text(encoding='utf-8'))
from PIL import Image,ImageDraw
im=Image.new('RGB',(1000,620),'white');dr=ImageDraw.Draw(im)
def plot(geom,color,view,dx):
 if geom.is_empty:return
 if hasattr(geom,'geoms'):
  for g in geom.geoms:plot(g,color,view,dx)
  return
 if geom.geom_type!='Polygon':return
 def xy(v):return(dx+(v[0]-view[0])*65,580-(v[1]-view[1])*65)
 dr.polygon([xy(v) for v in geom.exterior.coords],fill=color)
for view,dx,title in [((16,4.5,23,13),20,'U3 eFuse GND'),((20,50.5,27.5,59),510,'R12 / ESP GND')]:
 crop=box(*view)
 for q in pads:plot(q['geom'].intersection(crop),'#55bb66' if q['net']=='GND' else '#edaaaa',view,dx)
 for t in tracks:
  if t['layer']==1:plot(t['geom'].intersection(crop),'#225522' if t['net']=='GND' else '#d34f00',view,dx)
 for v in vias:plot(Point(v['x'],v['y']).buffer(.3).intersection(crop),'#3366aa' if v['net']=='GND' else '#aa44aa',view,dx)
 for q in pads:
  if view[0]<q['x']<view[2] and view[1]<q['y']<view[3]:dr.text((dx+(q['x']-view[0])*65,580-(q['y']-view[1])*65),q['ref']+':'+q['number'],fill='black')
 dr.text((dx,10),title,fill='black')
im.save(P/'reports/ground-routing-debug-v07.png')
