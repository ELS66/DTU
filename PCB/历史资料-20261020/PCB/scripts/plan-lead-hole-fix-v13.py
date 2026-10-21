exec(open('PCB/scripts/audit-lead-hole-model-v13.py',encoding='utf-8-sig').read().split("if __name__")[0])
from shapely.strtree import STRtree
from shapely.prepared import prep
import copy,math,zipfile
exec(Path('PCB/scripts/render-hy20-gerber-v13.py').read_text(encoding='utf8').split('for label,copper,mask,silk in')[0]);z.close();z=zipfile.ZipFile('PCB/eda/DTU-V0.13-60x70-Silkholefix-Gerber.zip');cache.clear();mask=unary_union([g for g,d in geom('Gerber_TopSolderMaskLayer.GTS')[0] if d]);result={}
for vid,ref in [('026b68367e7fffbc','Q1'),('bd31757caf9c21db','J4')]:
 v=next(v for v in plan['vias'] if v['id']==vid);selected=[r for r in plan['routes'] if any(math.dist(p,(v['x'],v['y']))<.01 for p in r['pointsMm'])];changed={r['id'] for r in selected};obs={}
 for layer in [1,2,15,16]:obs[layer]=unary_union([p['geom'] for p in pads if p['net']!=v['net'] and p['layer'] in [layer,12]]+[LineString(r['pointsMm']).buffer(r['widthMm']/2) for r in plan['routes'] if r['id'] not in changed and r['net']!=v['net'] and r['layer']==layer]+[Point(q['x'],q['y']).buffer(q['diameter']/2) for q in plan['vias'] if q['id']!=vid and q['net']!=v['net']])
 leads=unary_union([g['geom'] for g in lead_geoms if g['ref']==ref]);opts=[]
 for ix in range(-20,21):
  for iy in range(-20,21):
   x=round(v['x']+ix*.05,3);y=round(v['y']+iy*.05,3);pt=Point(x,y);ann=pt.buffer(.225)
   if pt.distance(leads)-.1<.3 or ann.distance(mask)<.16:continue
   if any(ann.distance(o)<.158 for o in obs.values()):continue
   if any(math.hypot(x-q['x'],y-q['y'])-.1-q['hole']/2<.25 for q in plan['vias'] if q['id']!=vid):continue
   updates=[];ok=True
   for r in selected:
    seq=[([x,y] if math.dist(p,(v['x'],v['y']))<.01 else p) for p in r['pointsMm']]
    if LineString(seq).buffer(r['widthMm']/2).distance(obs[r['layer']])<.155:ok=False;break
    updates.append({**r,'pointsMm':seq})
   if ok:opts.append({'x':x,'y':y,'distance':math.hypot(x-v['x'],y-v['y']),'leadHoleGapMm':pt.distance(leads)-.1,'annulusMaskGapMm':ann.distance(mask),'routes':updates})
 opts.sort(key=lambda q:q['distance']);result[vid]={'ref':ref,'old':v,'candidates':opts[:5]};print(ref,len(opts),[{k:v for k,v in q.items() if k!='routes'} for q in opts[:3]],flush=True)
Path('PCB/manifests/lead-hole-move-options-v13.json').write_text(json.dumps(result,indent=2))
