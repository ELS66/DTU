from pathlib import Path
p=Path('PCB/scripts/plan-fanout-v07.py');s=p.read_text(encoding='utf-8-sig');a=s.index("  r={**q");b=s.index("for t in old['lines']",a);s=s[:a]+'''  r={**q,'ref':c['ref'],'x':q['x']*.0254,'y':q['y']*.0254}
  if q['shape'][0]=='POLYGON':
   v=[x for x in q['shape'][1] if isinstance(x,(int,float))];pts=list(zip([x*.0254 for x in v[::2]],[x*.0254 for x in v[1::2]]));w=max(x[0] for x in pts)-min(x[0] for x in pts);h=max(x[1] for x in pts)-min(x[1] for x in pts)
  else:
   w,h=[x*.0254 for x in q['shape'][1:3]];ang=math.radians(q['rotation']);pts=[]
   for dx,dy in [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]:pts.append((r['x']+dx*math.cos(ang)-dy*math.sin(ang),r['y']+dx*math.sin(ang)+dy*math.cos(ang)))
  r['geom']=Polygon(pts);r['w']=w;r['h']=h;pads.append(r)
''' + s[b:];p.write_text(s,encoding='utf-8')
