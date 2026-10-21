import zipfile,json,collections
from pathlib import Path
P=Path('PCB');z=zipfile.ZipFile(P/'eda/DTU-V0.12-stage.epro2');s=z.read(next(n for n in z.namelist() if n.endswith('.epru'))).decode('utf-8');docs={};current=None
for line in s.splitlines():
    if '||' not in line:continue
    a,b=line.split('||',1)
    if not b.rstrip('|').strip():continue
    a=json.loads(a);b=json.loads(b.rstrip('|'))
    if a['type']=='DOCHEAD':
        current=docs.setdefault((b['docType'],b['uuid']),{})
    elif current is not None:
        key=(a['type'],a.get('id',''));old=current.get(key)
        if old is None or a.get('ticket',0)>=old[0].get('ticket',0):current[key]=(a,b)
cs=json.load(open(P/'manifests/pcb-pads-stage-v12.json',encoding='utf-8'))['result'];out={}
for c in cs:
    fp=c['footprint']['uuid'];rows=docs.get(('FOOTPRINT',fp),{});out[fp]=[{'type':a['type'],'id':a.get('id'),**b} for a,b in rows.values() if isinstance(b,dict)]
for c in cs:
    if c['ref'] in ['U1','U2','C80','C85','L1','J1','J4']:
        print(c['ref'],c['rotation'],c['footprint']['uuid'],json.dumps([r for r in out[c['footprint']['uuid']] if r['type'] in ['LINE','POLY','FILL','RECT'] and r.get('layerId') in [3,9]],ensure_ascii=True)[:1600])
(P/'manifests/footprint-geometries-v12.json').write_text(json.dumps(out,ensure_ascii=False),encoding='utf-8')
