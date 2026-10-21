"""Prepare guarded API edits for the approved V0.11 interface revision."""
import json
from pathlib import Path

ROOT = Path('PCB')
PROJECT = '1d7fb27b7ad9306bc25c90ee476429c9e681ffecce79136ba05149eca7bba1b0'
LIB = '0819f05c4eef4c71ace90d822a990e87'
FIELD = '31c8ed08a1998d0d'
MERGE = '8902a3019bd8d84c'
def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8-sig'))
def js(value):
    return json.dumps(value, ensure_ascii=False)
def write(name, content):
    (ROOT / 'scripts' / name).write_text(content, encoding='utf-8')
field = {c['ref']: c for c in read('manifests/field-before-v11.json')['result']}
selector = {c['ref']: c for c in read('manifests/selector-before-v11.json')['result']}
old = read('manifests/revision-v06.json')
removed = ['U14','D15','D16','D17','R102','R103','R105','R106','R107','R111','R112','R113','R117','R124','C100','C101','C102','C105','C110']
expected = {r: p for r,p in old['expected'].items() if r not in removed}
expected.update({
    'U6': {'1':'485_RX_RAW','2':'MCU_485_DE','3':'MCU_485_DE','4':'FIELD_TX','5':'GND','6':'RS485_A','7':'RS485_B','8':'VDD_3V3'},
    'U7': {'1':'232_C1P','2':'232_VPLUS','3':'232_C1N','4':'232_C2P','5':'232_C2N','6':'232_VMINUS','8':'GND','10':'GND','11':'FIELD_TX','12':'232_RX_RAW','13':'232_RIN','14':'232_TOUT','15':'GND','16':'VDD_3V3'},
    'U12': {'1':'485_RX_RAW','2':'GND','3':'232_RX_RAW','4':'FIELD_RX','5':'VDD_3V3','6':'TTL_RX_BUF'},
    'R38': {'1':'VDD_3V3','2':'485_RX_RAW'},
    'R100': {'1':'VDD_3V3','2':'RS485_A'},
    'R101': {'1':'RS485_B','2':'GND'},
})
plan = {'version':'V0.11','projectUuid':PROJECT,'baseVersion':'V0.10 PCB / V0.6 schematic',
        'removedThisRevision':removed,'removed':old['removed']+removed,'expected':expected,'dnp':old['dnp'],
        'changes':{'U6':'MAX3485ESA+','U7':'BL13232ETS','U12':'SN74LVC1G11DCKR','R100':'270R','R101':'270R'},
        'requirements':{'singleConnectedInterface':True,'powerOffBeforeSwitching':True,'TTL':'5V','RS485':'MCU frame DE; DI carries data','receiveMerge':'three-input AND, idle high'}}
(ROOT/'manifests/revision-v11.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
guard = f"if((await eda.dmt_Project.getCurrentProjectInfo())?.uuid!=={js(PROJECT)})throw Error('Wrong project');"
helpers = """
async function clearAttached(parts){const wires=await eda.sch_PrimitiveWire.getAll();const ids=new Set();for(const c of parts)for(const q of await c.getAllPins()){const x=q.getState_X(),y=q.getState_Y();for(const w of wires){const l=w.getState_Line(),ps=Array.isArray(l[0])?l:[l];if(ps.some(p=>{for(let i=0;i<p.length;i+=2)if(Math.abs(p[i]-x)<.001&&Math.abs(p[i+1]-y)<.001)return true;return false;}))ids.add(w.getState_PrimitiveId());}}if(ids.size&&!await eda.sch_PrimitiveWire.delete([...ids]))throw Error('Wire delete failed');}
async function wire(c,pins){for(const q of await c.getAllPins()){const net=pins[q.getState_PinNumber()];const a=q.toAsync();a.setState_NoConnected(!net);await a.done();if(net){const x=q.getState_X(),y=q.getState_Y(),r=q.getState_Rotation()*Math.PI/180;if(!await eda.sch_PrimitiveWire.create([x,y,x+Math.round(Math.cos(r))*20,y+Math.round(Math.sin(r))*20],net))throw Error('Wire failed');}}}
async function create(d,ref,uid,x,y,name){const c=await eda.sch_PrimitiveComponent.create(d,x,y,undefined,0,false,true,true);if(!c)throw Error('Create failed '+ref);const p={designator:ref,uniqueId:uid};if(name)p.name=name;if(!await eda.sch_PrimitiveComponent.modify(c,p))throw Error('Properties failed');return c;}
"""
devices = {'U6':'92e94c6c12364f36970580043d5f88af','U7':'785967b7477c477bb4c234dc88df5709','U12':'27376aeb8ef24d0493ee69f282c2787f','R100':'9c489dbe92ab4589b18c64c0661a7b31','R101':'9c489dbe92ab4589b18c64c0661a7b31'}
code = guard + f"await eda.dmt_EditorControl.openDocument({js(FIELD)});" + helpers
code += "const parts=await eda.sch_PrimitiveComponent.getAll('part');const refs=['U6','U7','U12','R38'];await clearAttached(parts.filter(c=>refs.includes(c.getState_Designator())));for(const c of parts)if(['U6','U7','U12'].includes(c.getState_Designator()))if(!await eda.sch_PrimitiveComponent.delete(c))throw Error('Delete failed');"
for ref in ['U6','U7']:
    c = field[ref]
    code += f"{{const c=await create({js({'libraryUuid':LIB,'uuid':devices[ref]})},{js(ref)},{js(c['uid'])},{c['x']},{c['y']});await wire(c,{js(expected[ref])});}}"
code += f"const r=(await eda.sch_PrimitiveComponent.getAll('part')).find(c=>c.getState_Designator()==='R38');await wire(r,{js(expected['R38'])});return {{saved:await eda.sch_Document.save()}};"
write('revise-field-v11.js',code)
code = guard + f"await eda.dmt_EditorControl.openDocument({js(MERGE)});" + helpers
code += "const ps=await eda.sch_PrimitiveComponent.getAll('part');const ws=await eda.sch_PrimitiveWire.getAll();if(ws.length&&!await eda.sch_PrimitiveWire.delete(ws))throw Error('Wires failed');for(const c of ps)if(!await eda.sch_PrimitiveComponent.delete(c))throw Error('Part delete failed');const ts=await eda.sch_PrimitiveText.getAll();if(ts.length&&!await eda.sch_PrimitiveText.delete(ts))throw Error('Text delete failed');"
code += f"const gate=await create({js({'libraryUuid':LIB,'uuid':devices['U12']})},'U12',{js(field['U12']['uid'])},650,340);await wire(gate,{js(expected['U12'])});"
c=selector['R121']
code += f"const r=await create({js({'libraryUuid':PROJECT,'uuid':c['component']['uuid']})},'R121',{js(c['uid'])},500,680,'100k');await wire(r,{js(expected['R121'])});"
notes=[(160,100,'V0.11 三路接收合并 / 无需接口选择',18,True),
       (160,180,'FIELD_RX = 485_RX_RAW AND 232_RX_RAW AND TTL_RX_BUF',13,False),
       (160,230,'三路接收源各接独立输入；任一路为低，主控RX为低。',12,False),
       (160,500,'U12：3.3V供电，输入容忍5.5V；C38位于接口页并靠近芯片。',12,False),
       (160,560,'R38上拉485_RX_RAW，保证RS485发送期间接收输出高阻时输入不悬空。',12,False),
       (160,610,'RS485的DE与/RE由MCU_485_DE共同控制；R121保证上电默认接收。',12,False),
       (160,830,'约束：一次只连接并供电一个业务接口；断电后切换。',13,True),
       (160,880,'保留5V TTL发送转换、电源防倒灌、端口保护及独立GPIO指示灯。',12,False),
       (160,930,'RS485继续按帧控制方向，等待最后停止位发送完毕后回到接收。',12,False)]
for x,y,t,s,b in notes:
    code += f"await eda.sch_PrimitiveText.create({x},{y},{js(t)},0,null,null,{s},{js(b)});"
code += f"await eda.dmt_Schematic.modifySchematicPageName({js(MERGE)},'06_Receive_Merge');return {{saved:await eda.sch_Document.save(),parts:(await eda.sch_PrimitiveComponent.getAll('part')).map(c=>c.getState_Designator())}};"
write('revise-receive-merge-v11.js',code)
code = guard + f"await eda.dmt_EditorControl.openDocument({js(FIELD)});" + helpers
for ref,x,y in [('R100',540,1400),('R101',860,1400)]:
    code += f"{{const c=await create({js({'libraryUuid':LIB,'uuid':devices[ref]})},{js(ref)},{js(selector[ref]['uid'])},{x},{y},'270R');await wire(c,{js(expected[ref])});}}"
code += "await eda.sch_PrimitiveText.create(1060,1400,'R100/R101：RS485空闲偏置，270R；R32为终端DNP。',0,null,null,12);return {saved:await eda.sch_Document.save()};"
write('add-rs485-bias-v11.js',code)
write('export-full-schematic-v11.js',guard+f"await eda.dmt_EditorControl.openDocument({js(MERGE)});const f=await eda.sch_ManufactureData.getNetlistFile('full-schematic-v11','EasyEDA');if(!f)throw Error('Missing netlist');return {{name:f.name,content:await f.text()}};")
write('check-schematic-erc-v11.js',guard+"return await eda.sch_Drc.check(true,false,true);")
print('Prepared guarded edits; expected physical parts:',len(expected),'removed:',len(removed))
