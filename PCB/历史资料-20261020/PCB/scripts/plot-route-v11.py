from pathlib import Path
exec(Path('PCB/scripts/debug-route-v11.py').read_text().split(";net='232_VPLUS'")[0])
import matplotlib.pyplot as plt
fig,ax=plt.subplots(figsize=(10,8))
for k,col in [(1,'red'),(2,'blue')]:
 obs=obstacles('232_VPLUS',k)
 for g in obs.geoms:
  if g.geom_type=='Polygon':ax.fill(*g.exterior.xy,color=col,alpha=.22)
for p in pads:
 if 24<p['x']<34 and 6<p['y']<20:ax.annotate(p['ref']+'.'+p['number'],(p['x'],p['y']),fontsize=7)
ax.set_xlim(24,34);ax.set_ylim(6,20);ax.set_aspect('equal');fig.savefig('PCB/reports/route-debug-v11.png',dpi=130)
