"""Produce a native project with only the three field-terminal legends."""
from pathlib import Path
import json,zipfile,collections,base64

R=Path('PCB');E=R/'eda';M=R/'manifests'
source=E/'DTU-V0.13-60x70-Exposurefix.epro2'
target=E/'DTU-V0.13-60x70-Silkclean-input.epro2'
keep={'26597142481c5bca','8fade49b3aaf5333','fd940d048c851faf','1c40b1cf5135c2f6','21fa6d8d887b76eb',
      '62b0edbae000f665','51221ba26a2bbfe8','dda43bdab91500e1','f149ee9fd7cbc189','5eab927c5d08c175',
      'fd9e533e11aec707','f92d5823211de0ca','af0721377e1b892a','3b094ed814d9ee1d','11a2348a2a2abbb3'}
graphics={'POLY','FILL','LINE','ARC','CARC','CIRCLE','STRING','REGION','IMAGE','OBJECT','DIMENSION'}
def record(line):
    if '||' not in line:return None
    h,b=line.split('||',1);h=json.loads(h)
    if b in ['','|','""','""|']:return h,None
    return h,json.loads(b.removesuffix('|'))
z=zipfile.ZipFile(source);name=next(n for n in z.namelist() if n.endswith('.epru'))
blocks=[];block=[]
for line in z.read(name).decode('utf8').splitlines():
    item=record(line)
    if item and item[0]['type']=='DOCHEAD' and block:blocks.append(block);block=[]
    block.append(line)
if block:blocks.append(block)
out=[];removals=[];hidden=[]
for block in blocks:
    item=record(block[0]);doc=item[1] if item and item[0]['type']=='DOCHEAD' else None
    out.extend(block)
    if not doc or doc.get('docType') not in ['PCB','FOOTPRINT']:continue
    state={};maximum=0
    for line in block:
        item=record(line)
        if not item:continue
        h,b=item;maximum=max(maximum,h.get('ticket',0))
        if h['type']=='DOCHEAD':continue
        key=(h['type'],h.get('id',''))
        if key not in state or h.get('ticket',0)>=state[key][0].get('ticket',0):state[key]=(h,b)
    for (kind,id),(h,b) in state.items():
        if not isinstance(b,dict) or b.get('layerId') not in [3,4]:continue
        if kind in graphics and not (doc['docType']=='PCB' and kind=='STRING' and id in keep):
            maximum+=1;meta={**h,'ticket':maximum}
            # Empty-body tombstones follow this installed 4.1.71 export's syntax.
            out.append(json.dumps(meta,separators=(',',':'))+'|||')
            removals.append({'docType':doc['docType'],'document':doc['uuid'],'type':kind,'id':id})
        elif kind=='ATTR' and (b.get('keyVisible') or b.get('valueVisible')):
            maximum+=1;body={**b,'keyVisible':False,'valueVisible':False}
            out.append(json.dumps({**h,'ticket':maximum},separators=(',',':'))+'||'+json.dumps(body,ensure_ascii=False,separators=(',',':'))+'|')
            hidden.append({'document':doc['uuid'],'id':id})
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as q:
    for n in z.namelist():q.writestr(n,('\n'.join(out)+'\n').encode('utf8') if n==name else z.read(n))
z.close()
(M/'silkclean-input-edits-v13.json').write_text(json.dumps({'source':str(source.resolve()),'target':str(target.resolve()),'removed':removals,'hiddenAttributeVisibility':hidden,'keptPCBTextIds':sorted(keep),'factoryDfmPassed':False},ensure_ascii=False,indent=2),encoding='utf8')
folder=str((R/'native-Silkclean').resolve());Path(folder).mkdir(exist_ok=True)
code="if((await eda.dmt_Project.getCurrentProjectInfo())?.uuid!=='52c709566e222603927d1a7d15a5e220a7f38cb78f29ecab14bf35ab4cfcb0b9')throw Error('Wrong source project');const encoded="+json.dumps(base64.b64encode(target.read_bytes()).decode())+";const bytes=Uint8Array.from(atob(encoded),c=>c.charCodeAt(0));const file=new File([bytes],'DTU-V0.13-60x70-Silkclean.epro2',{type:'application/octet-stream'});const imported=await eda.sys_FileManager.importProjectByProjectFile(file,'JLCEDA Pro',{importOption:'ImportDocument',associateFootprint:true,associate3DModel:true,importFootprintNotesLayer:true},{operation:'Offline Client Local Path',folderPath:"+json.dumps(folder)+"});return {imported};"
(R/'scripts/import-silkclean-native-v13.js').write_text(code,encoding='utf8')
print(json.dumps({'removedGraphics':len(removals),'hiddenAttributes':len(hidden),'keptPCBText':len(keep),'byDocType':dict(collections.Counter(r['docType'] for r in removals)),'nativeProjectInput':str(target)},ensure_ascii=True))
