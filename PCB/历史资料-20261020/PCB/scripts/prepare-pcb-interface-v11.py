"""Synchronize actual V0.11 schematic devices and prune obsolete copper."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path('PCB/.tools').resolve()))
from shapely.geometry import Polygon,LineString,Point
from shapely.ops import unary_union
P=Path('PCB')
def read(n): return json.loads((P/n).read_text(encoding='utf-8-sig'))
plan=read('manifests/revision-v11.json')
schematic=read('reports/full-schematic-v11.net')
parts={c['props']['Designator']:c for c in schematic['components'].values()}
pcb=read('manifests/pcb-pads-before-v11.json')['result']
old={c['ref']:c for c in pcb}
routing=read('manifests/routing-before-v11.json')['result']
def padgeom(p):
    import math
    if p['shape'][0]=='POLYGON':
        v=[x for x in p['shape'][1] if isinstance(x,(int,float))]
        return Polygon(list(zip(v[::2],v[1::2])))
    w,h=p['shape'][1:3];a=math.radians(p['rotation']);x,y=p['x'],p['y']
    return Polygon([(x+dx*math.cos(a)-dy*math.sin(a),y+dx*math.sin(a)+dy*math.cos(a)) for dx,dy in [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]])
reroute={'FIELD_RX','TTL_RX_BUF','232_C1P','232_C1N','232_C2P','232_C2N','232_VPLUS','232_VMINUS','232_TOUT','232_RIN'}
allnets={v for pins in plan['expected'].values() for v in pins.values()}
stale={p['net'] for c in pcb for p in c['pads'] if p['net'] and p['net'] not in allnets}
changed=[]
for ref in ['U7','U12']:
    for p in old[ref]['pads']:
        if p['net'] and (plan['expected'][ref].get(p['number'],'')!=p['net'] or ref=='U12'):
            changed.append((p['net'],padgeom(p).buffer(1)))
def points(t):
    if 'polygon' not in t:return [(t['x1'],t['y1']),(t['x2'],t['y2'])]
    a=t['polygon'];v=[x for x in a[3:] if isinstance(x,(int,float))]
    return [(a[0],a[1])]+list(zip(v[::2],v[1::2]))
delete={'lines':[],'polys':[],'vias':[]}
for kind in ['lines','polys']:
    for t in routing[kind]:
        if t['layer'] not in [1,2,15,16]:continue
        g=LineString(points(t)).buffer(t['width']/2)
        if t['net'] in stale|reroute or any(t['net']==n and g.intersects(p) for n,p in changed):delete[kind].append(t['id'])
for v in routing['vias']:
    if v['net'] in stale|reroute:delete['vias'].append(v['id'])
placements={'U6':(old['U6']['x'],old['U6']['y'],270),
            'U7':(old['U7']['x'],old['U7']['y'],old['U7']['rotation']),
            'U12':(old['U12']['x'],old['U12']['y'],90),
            'R100':(3.1/.0254,15.2/.0254,0),
            'R101':(8.3/.0254,19.1/.0254,90)}
specs=[]
for ref,(x,y,a) in placements.items():
    prop=parts[ref]['props']
    other={k:v for k,v in prop.items() if k not in ['Unique ID','Name','Designator','Manufacturer','Manufacturer Part','Supplier','Supplier Part','Add into BOM','Convert to PCB']}
    specs.append({'ref':ref,'device':prop['Device'],'x':x,'y':y,'rotation':a,
                  'props':{'designator':ref,'uniqueId':prop['Unique ID'],'name':prop['Name'],
                           'manufacturer':prop.get('Manufacturer',''),
                           'manufacturerId':prop['Manufacturer Part'],'supplier':'LCSC','supplierId':prop['Supplier Part'],
                           'addIntoBom':True,'otherProperty':other}})
guard=f"if((await eda.dmt_Project.getCurrentProjectInfo())?.uuid!=={json.dumps(plan['projectUuid'])}||(await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=='4211128ecf040c100b33238447713203')throw Error('Wrong PCB');"
remove=plan['removedThisRevision']+list(placements)
code=guard+'const remove='+json.dumps(remove)+';const deleteCopper='+json.dumps(delete)+';'
code+="const components=await eda.pcb_PrimitiveComponent.getAll();const ids=components.filter(c=>remove.includes(c.getState_Designator())).map(c=>c.getState_PrimitiveId());if(ids.length&&!await eda.pcb_PrimitiveComponent.delete(ids))throw Error('Component deletion failed');for(const [kind,api] of [['lines',eda.pcb_PrimitiveLine],['polys',eda.pcb_PrimitivePolyline],['vias',eda.pcb_PrimitiveVia]])if(deleteCopper[kind].length&&!await api.delete(deleteCopper[kind]))throw Error('Copper deletion failed '+kind);return {removed:ids.length,copper:Object.fromEntries(Object.entries(deleteCopper).map(([k,v])=>[k,v.length])),saved:await eda.pcb_Document.save()};"
(P/'scripts/prune-pcb-interface-v11.js').write_text(code,encoding='utf-8')
code=guard+'const specs='+json.dumps(specs,ensure_ascii=False)+';const project='+json.dumps(plan['projectUuid'])+';const map='+json.dumps(plan['expected'])+';'
code+="for(const s of specs){const c=await eda.pcb_PrimitiveComponent.create({libraryUuid:project,uuid:s.device},1,s.x,s.y,s.rotation,false);if(!c)throw Error('Create failed '+s.ref);if(!await eda.pcb_PrimitiveComponent.modify(c,s.props))throw Error('Properties failed');}for(const c of await eda.pcb_PrimitiveComponent.getAll()){const ref=c.getState_Designator();if(!map[ref])throw Error('Unexpected ref '+ref);for(const pin of await eda.pcb_PrimitiveComponent.getAllPinsByPrimitiveId(c.getState_PrimitiveId())){const net=map[ref][pin.getState_PadNumber()]||'';if(pin.getState_Net()!==net){const a=pin.toAsync();a.setState_Net(net);await a.done();}}}return {saved:await eda.pcb_Document.save(),parts:(await eda.pcb_PrimitiveComponent.getAll()).length};"
(P/'scripts/sync-pcb-interface-v11.js').write_text(code,encoding='utf-8')
(P/'manifests/pcb-edit-plan-v11.json').write_text(json.dumps({'staleNets':sorted(stale),'reroutedNets':sorted(reroute),'delete':delete,'placements':placements},indent=2),encoding='utf-8')
print('Prune copper:',{k:len(v) for k,v in delete.items()},'stale nets',len(stale))
