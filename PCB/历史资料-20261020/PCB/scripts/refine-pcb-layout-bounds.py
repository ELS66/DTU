from pathlib import Path
p=Path('PCB/scripts/prepare-pcb-layout-v04.py');s=p.read_text(encoding='utf-8-sig');s=s.replace("'U2':(39,44,0)","'U2':(39,40,0)").replace("'J5':(53,51,0)","'J5':(53,47,0)").replace("'J6':(50.6,12,90)","'J6':(49.7,10,90)").replace("'J7':(50.6,25,90)","'J7':(49.7,21,90)").replace("'U4':(23,53.5,0)","'U4':(30,61,0)").replace("'L1':(25.5,61,0)","'L1':(37,60,0)").replace("'C80':(39.5,61,0)","'C80':(47,60,0)").replace("'L3':(14,13,0)","'L3':(13,17.8,0)").replace("'U13':(23.5,23,0)","'U13':(21,24.8,0)").replace("'U9':(40,22,0)","'U9':(40,21,0)").replace("'U14':(33,26,0)","'U14':(33,22,0)").replace("'U10':(21.8,31,0)","'U10':(21.8,33.3,0)")
s=s.replace("W,H=55,65;placed={};bboxes={};fail=[]",'''W,H=55,65;placed={};bboxes={};fail=[]
for c in cs:
 ref=c['ref']
 if ref[0]in 'UJL'or ref=='C80':continue
 pts=[]
 for pad in c['pads']:
  shape=pad['shape'];w=shape[1];h=shape[2];a=math.radians(pad['rotation'])
  for dx in [-w/2,w/2]:
   for dy in [-h/2,h/2]:pts.append((pad['x']+dx*math.cos(a)-dy*math.sin(a),pad['y']+dx*math.sin(a)+dy*math.cos(a)))
 b={'minX':min(p[0]for p in pts)-3,'minY':min(p[1]for p in pts)-3,'maxX':max(p[0]for p in pts)+3,'maxY':max(p[1]for p in pts)+3}
 if ref.startswith('SW'):
  b['minY']=min(b['minY'],c['y']-1.8/.0254);b['maxY']=max(b['maxY'],c['y']+1.8/.0254)
 if ref in ['D1','D2','D3']:
  b['minY']=min(b['minY'],c['y']-1.4/.0254);b['maxY']=max(b['maxY'],c['y']+1.4/.0254)
 c['bbox']=b''')
p.write_text(s,encoding='utf-8')
