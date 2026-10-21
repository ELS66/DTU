from pathlib import Path
exec(Path('PCB/scripts/router-v13.py').read_text(encoding='utf8'))

plan=json.load(open(P/'manifests/smd70-connected-routing-v13.json',encoding='utf8'))
clusters=[]
for v in plan['vias']:
    cluster=next((g for g in clusters if g[0]['net']==v['net'] and math.dist((g[0]['x'],g[0]['y']),(v['x'],v['y']))<.12),None)
    if cluster is None: clusters.append([v])
    else: cluster.append(v)
keep=[]
for group in clusters:
    chosen=dict(group[-1])
    chosen["x"]=sum(q["x"] for q in group)/len(group)
    chosen["y"]=sum(q["y"] for q in group)/len(group)
    keep.append(chosen)
    for old in group:
        for r in plan['routes']:
            if r['net']==old['net']:
                r['pointsMm']=[(chosen['x'],chosen['y']) if math.dist(pt,(old['x'],old['y']))<.001 else pt for pt in r['pointsMm']]
clean=[]
for r in plan['routes']:
    pts=[pt for i,pt in enumerate(r['pointsMm']) if i==0 or math.dist(pt,r['pointsMm'][i-1])>.00001]
    if len(pts)<2: continue
    r['pointsMm']=pts
    clean.append(r)
print('Removed duplicate vias',len(plan['vias'])-len(keep),'remaining',len(keep),flush=True)
plan['routes']=clean
plan['vias']=keep
(P/'manifests/smd70-connected-routing-v13.json').write_text(json.dumps(plan,indent=2))
