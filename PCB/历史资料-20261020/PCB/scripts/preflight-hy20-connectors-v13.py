from pathlib import Path
import json,copy,math
P=Path('PCB');cs=copy.deepcopy(json.loads((P/'manifests/pads-after-routing-opt-v13.json').read_text(encoding='utf8'))['result'])
src=json.loads((P/'manifests/hy20-calibrated-footprint-source-v13.json').read_text(encoding='utf8'))['result']['source'];fp=[]
for l in src.splitlines():
 if l.startswith('{"type":"PAD"'):
  h,z=l.split('||',1);fp.append(json.loads(z.removesuffix('|')))
for c in cs:
 if c['ref'] not in ['J1','J2','J3']:continue
 c['y']=5/.0254;c['rotation']=0;c['footprint']={'libraryUuid':'52c709566e222603927d1a7d15a5e220a7f38cb78f29ecab14bf35ab4cfcb0b9','uuid':'80c4e7847cda6643','name':'DTU_HY2.0_4P_LT_ZX_DRAWING'}
 old={q['number']:q for q in c['pads']};c['pads']=[]
 for q in fp:
  pad=q['defaultPad'];c['pads'].append({'id':'HY_'+c['ref']+'_'+q['num'],'number':q['num'],'net':old[q['num']]['net'],'x':c['x']+q['centerX'],'y':c['y']+q['centerY'],'rotation':0,'shape':['RECT',pad['width'],pad['height'],0],'layer':1})
(P/'manifests/hy20-proposed-pads-v13.json').write_text(json.dumps({'result':cs},indent=2),encoding='utf8')
exec((P/'scripts/router-v13.py').read_text(encoding='utf8').replace('read-pcb-pads-v13.json','hy20-proposed-pads-v13.json'))
plan=load_plan(P/'manifests/routing-optimized-source-v13.json');conflicts=[];vip=[]
for p in pads:
 if p['ref'] not in ['J1','J2','J3']:continue
 for i,r in enumerate(plan['routes']):
  if r['layer']!=1 or (p['net'] and r['net']==p['net']):continue
  d=p['geom'].distance(LineString(r['pointsMm']).buffer(r['widthMm']/2))
  if d<.153:conflicts.append({'pad':p['ref']+':'+p['number'],'kind':'route','index':i,'net':r['net'],'distance':d})
 for i,v in enumerate(plan['vias']):
  d=p['geom'].distance(Point(v['x'],v['y']).buffer(v['diameter']/2))
  if d<.153 and (not p['net'] or v['net']!=p['net']):conflicts.append({'pad':p['ref']+':'+p['number'],'kind':'via','index':i,'net':v['net'],'distance':d})
  if d<.1:vip.append({'pad':p['ref']+':'+p['number'],'via':v})
print('Copper conflicts',len(conflicts),conflicts,flush=True);print('Vias overlapping/near pads',len(vip),vip,flush=True)
(P/'manifests/hy20-preflight-v13.json').write_text(json.dumps({'conflicts':conflicts,'viasNearPads':vip},indent=2),encoding='utf8')
