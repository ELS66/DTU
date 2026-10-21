from pathlib import Path
p=Path('PCB/scripts/plan-power-routing-v07.py');s=p.read_text(encoding='utf-8-sig');s=s.replace(" if m[s[1],s[0]] or m[t[1],t[0]]:return None",''' def seed(pt,cell):
  if not m[cell[1],cell[0]]:return cell
  opts=[(math.dist(pt,(x*step,y*step)),(x,y)) for x in range(cell[0]-2,cell[0]+3) for y in range(cell[1]-2,cell[1]+3) if 0<x<nx-1 and 0<y<ny-1 and not m[y,x] and math.dist(pt,(x*step,y*step))<.25]
  return min(opts)[1] if opts else None
 s=seed(a,s);t=seed(b,t)
 if s is None or t is None:return None''');s=s.replace("   seq=seq[::-1];out=[list(a)];last=None", "   seq=seq[::-1];out=[list(a),[s[0]*step,s[1]*step]];last=None")
s=s.replace(" new.append({'net':net,'layer':layer,'pointsMm':pts,'widthMm':width});tracks.append", " if new and new[-1]['net']==net and new[-1]['layer']==layer and new[-1]['widthMm']==width and math.dist(new[-1]['pointsMm'][-1],pts[0])<1e-8:new[-1]['pointsMm'].extend(pts[1:])\n else:new.append({'net':net,'layer':layer,'pointsMm':pts,'widthMm':width})\n tracks.append")
s=s.replace(" mask,obs=raster(net,16,.35);conn=", " mask,obs=raster(net,16,.35);bottom,obsbottom=raster(net,2,.35);conn=")
s=s.replace("  if pts is None:fails.append({'net':net,'from':a,'to':b});conn.append(b);continue", "  layer=16;edgeobs=obs\n  if pts is None:pts=astar(a,b,bottom);layer=2;edgeobs=obsbottom\n  if pts is None:fails.append({'net':net,'from':a,'to':b});conn.append(b);continue")
s=s.replace("LineString([last,end]).distance(obs)-.175", "LineString([last,end]).distance(edgeobs)-.175").replace("add(net,16,[list(last),end]", "add(net,layer,[list(last),end]")
p.write_text(s,encoding='utf-8')
