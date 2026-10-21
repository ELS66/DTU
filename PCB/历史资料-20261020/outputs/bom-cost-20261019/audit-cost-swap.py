from pathlib import Path
import hashlib, json, zipfile, csv

root=Path('D:/DTU')
out=root/'outputs/bom-cost-20261019'
manifest=json.loads((root/'PCB/manifests/current-pcb-delivery.json').read_text(encoding='utf8'))
native=Path(manifest['nativeProject'])
with zipfile.ZipFile(native) as z:
    source=z.read(next(n for n in z.namelist() if n.endswith('.epru'))).decode('utf8')
active={}; doc=None
for line in source.splitlines():
    if '||' not in line: continue
    head,body=line.split('||',1)
    head=json.loads(head)
    try: body=json.loads(body.removesuffix('|'))
    except ValueError: body=None
    if head['type']=='DOCHEAD':
        doc=(body['docType'],body['uuid']); continue
    key=(*doc,head['type'],head.get('id',''))
    if body is None: active.pop(key,None)
    else: active[key]=body
pcb=manifest['pcbUuid']
ref=next(p for k,p in active.items() if k[:3]==('PCB',pcb,'ATTR') and p.get('key')=='Designator' and p.get('value')=='U6')
cid=ref['parentId']
attrs={p['key']:p['value'] for k,p in active.items() if k[:3]==('PCB',pcb,'ATTR') and p.get('parentId')==cid}
fp=attrs['Footprint']
netmap={}
for key,p in active.items():
    if key[:3]!=('PCB',pcb,'PAD_NET'): continue
    ident=json.loads(key[3])
    if ident[1]==cid: netmap[ident[2]]=p['padNet']
expected={'1':'485_RX_RAW','2':'MCU_485_DE','3':'MCU_485_DE','4':'FIELD_TX','5':'GND','6':'RS485_A','7':'RS485_B','8':'VDD_3V3'}
assert netmap==expected,(netmap,expected)
pins={'1':'RO','2':'/RE','3':'DE','4':'DI','5':'GND','6':'A','7':'B','8':'VCC'}
padrows=[]
for key,p in active.items():
    if key[:3]!=('FOOTPRINT',fp,'PAD'): continue
    num=p['num']; x=p['centerX']*.0254; y=p['centerY']*.0254
    w=p['defaultPad']['width']*.0254; h=p['defaultPad']['height']*.0254
    assert abs(abs(y)-2.450084)<.0001
    assert abs(w-.6)<.00001 and abs(h-1.8)<.00001
    assert abs(abs(x)-(.635 if num in ['2','3','6','7'] else 1.905))<.00001
    # NSOIC8 POD-00000108: nominal E=6.00 mm; max b=.51 mm; max L=1.27 mm.
    transverse_margin=(w-.51)/2
    land_inner=abs(y)-h/2; land_outer=abs(y)+h/2
    lead_inner=3-1.27; lead_outer=3
    assert transverse_margin>0 and lead_inner>=land_inner and lead_outer<=land_outer
    padrows.append({'pin':num,'function':pins[num],'net':netmap[num], 'centerLocalMm':[x,y], 'landSizeMm':[w,h], 'transverseNominalLeadMarginMm':transverse_margin,'landRadialMm':[land_inner,land_outer],'referenceLeadRadialMm':[lead_inner,lead_outer]})
assert len(padrows)==8
preserved=[]
for record in manifest['files']:
    if not record['file'].endswith(('.epro2','Gerber.zip','BOM-99.csv','CPL-99-Top.csv')): continue
    path=native.parent/record['file']
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest==record['sha256']
    preserved.append({'file':record['file'],'sha256':digest})
with (root/'PCB/eda/DTU-V0.14.4-Threefix-BOM-99.csv').open(encoding='utf-8-sig',newline='') as f:
    bom=list(csv.DictReader(f))
assert len(bom)==99 and next(p for p in bom if p['Designator']=='U6')['LCSC Part #']=='C1545222'
report={'date':'2026-10-19','status':'Procurement candidate; reference-level pin and nominal mechanical review completed; no assembled-board test performed', 'referenceNative':str(native),'referenceRevision':manifest['revision'], 'component':'U6','oldModel':'MAX3485ESA+','oldCode':'C1545222','sameChipReelModel':'MAX3485ESA+T','sameChipReelCode':'C18148','candidateModel':'SP3485EN-L/TR','candidateCode':'C8963','manufacturer':'MaxLinear','existingFootprint':fp,'pinMap':pins,'netMap':netmap,'pads':sorted(padrows,key=lambda p:int(p['pin'])),'oldSupplyV':[3.0,3.6],'candidateCharacterizedSupplyV':[3.135,3.465],'temperatureC':[-40,85],'dataRateMbps':10,'pcbGeometryChanged':False,'referenceArtifactsUnchanged':preserved,'limitations':['Nominal geometric review, not complete mechanical tolerance-stack or factory assembly qualification.','Candidate supply characterization is narrower than original. Measure 3.3V rail under LTE and Wi-Fi load.','Verify required baud rates, direction turnaround, idle behavior and field cable operation on first boards.','RMB purchase price, minimum order, spare quantities and SMT charges require an actual quotation.']}
(out/'U6-replacement-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'pins':len(netmap),'lands':len(padrows),'minimumTransverseNominalLeadMarginMm':min(p['transverseNominalLeadMarginMm'] for p in padrows),'referenceArtifactsUnchanged':len(preserved),'newCandidate':'SP3485EN-L/TR C8963'},ensure_ascii=False))
