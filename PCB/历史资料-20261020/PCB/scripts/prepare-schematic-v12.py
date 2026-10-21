"""Compile reviewed electrical deltas into single-use, project-guarded API edits."""
import json, copy
from pathlib import Path
P=Path('PCB'); PROJECT='be907e0c26ece4ccdedd2f5b24e25f76812bc6b957961675838d5450e3220cbc'; LIB='0819f05c4eef4c71ace90d822a990e87'
def read(n):return json.loads((P/n).read_text(encoding='utf-8-sig'))
def js(o):return json.dumps(o,ensure_ascii=False)
old=read('manifests/revision-v11.json'); plan=copy.deepcopy(old);plan.update(version='V0.12',projectUuid=PROJECT,baseVersion='V0.11')
n=json.loads(read('manifests/schematic-before-v12.json')['result']['content']); parts={c['props']['Designator']:c for c in n['components'].values() if not c['props']['Designator'].startswith('PROBE')}
e=plan['expected'];remove=['Q3','R74','R75','R76'];plan['removedThisRevision']=remove
for r in remove:e.pop(r,None)
e['U2']={k:'GND' for k in ['1','10','27','34','36','37','40','41','45','46','47','48','70','71','72','73','88','89','90','91','92','93','94','95']}
e['U2'].update({'7':'LTE_PWRKEY','11':'SIM_DATA_M','12':'SIM_RST_M','13':'SIM_CLK_M','14':'SIM_VDD','15':'LTE_RESET','17':'LTE_RXD','18':'LTE_TXD','24':'LTE_VDD_EXT','35':'LTE_ANT','42':'VDD_4G','43':'VDD_4G','59':'LTE_USB_DP','60':'LTE_USB_DM','61':'LTE_USB_VBUS','79':'SIM_DET','82':'LTE_BOOT'})
e['U10']={'1':'VDD_3V3','2':'GND','3':'MCU_LTE_TX','4':'LTE_RX_SER','5':'VDD_3V3','6':'LTE_VDD_EXT'}
e['U13']={'1':'VDD_3V3','2':'GND','3':'MCU_LTE_RX','4':'LTE_TX_SER','5':'GND','6':'LTE_VDD_EXT'}
e['R64']={'1':'LTE_BOOT_FIXTURE','2':'LTE_BOOT'}
e['SW4']={'1':'LTE_BOOT_FIXTURE','2':'LTE_BOOT_FIXTURE','3':'GND','4':'GND'}
e['J7']={'1':'GND','2':'LTE_USB_DP_EXT','3':'LTE_USB_DM_EXT','4':'LTE_USB_VBUS','5':'LTE_BOOT_FIXTURE'}
e['R55']={'1':'LTE_VDD_EXT','2':'SIM_DET'}
for r,net in [('C85','VDD_4G'),('C71','LTE_VDD_EXT'),('C72','VDD_3V3'),('C73','LTE_VDD_EXT'),('C56','SIM_DATA'),('C57','SIM_RST')]:e[r]={'1':net,'2':'GND'}
e['R77']={'1':'LTE_VDD_EXT','2':'LTE_RXD'};e['R78']={'1':'LTE_VDD_EXT','2':'GND'}
e['J1']={'1':'VIN_485','2':'RS485_A_EXT','3':'RS485_B_EXT','4':'GND'}
e['J2']={'1':'VIN_232','2':'RS232_TX_EXT','3':'RS232_RX_EXT','4':'GND'}
e['J3']={'1':'VIN_TTL','2':'TTL_TX_EXT','3':'TTL_RX_EXT','4':'GND'}
plan['dnp']=['J6','J7','R32','C50','C51'];plan['requirements'].update(boardTargetMm=[50,60],mountingHoles={'diameterMm':3.2,'edgeInsetMm':4,'plated':False},downloadPitchMm=2.54,fieldPitchMm=2.0,fieldPhysicalOrder='PABG/PTRG/PTRG; left to right viewed from component side',uartTranslation='two fixed-direction SN74LVC1T45; 3.3V/1.8V; supply-off isolation',lteBoot='LOW before power on',ledPlacement='LTE left edge, ESP right edge, mirrored; TX/RX below ESP')
plan['changes'].update({'U2':'ML307R-DL','U4':'AP63300WU-7','U10':'SN74LVC1T45DCKR','U13':'SN74LVC1T45DCKR','L1':'SWPA8040S6R8MT','R55':'10k','R64':'1k','C85':'6SVPC220MV','C55':'33pF','C56':'33pF','C57':'33pF'})
(P/'manifests/revision-v12.json').write_text(js(plan),encoding='utf-8')
helpers="""async function clearAttached(parts){const wires=await eda.sch_PrimitiveWire.getAll();const ids=new Set();for(const c of parts)for(const q of await c.getAllPins()){const x=q.getState_X(),y=q.getState_Y();for(const w of wires){const l=w.getState_Line(),ps=Array.isArray(l[0])?l:[l];if(ps.some(p=>{for(let i=0;i<p.length;i+=2)if(Math.abs(p[i]-x)<.001&&Math.abs(p[i+1]-y)<.001)return true;return false;}))ids.add(w.getState_PrimitiveId());}}if(ids.size&&!await eda.sch_PrimitiveWire.delete([...ids]))throw Error('Wire delete failed');}async function wire(c,pins){for(const q of await c.getAllPins()){const net=pins[q.getState_PinNumber()];const a=q.toAsync();a.setState_NoConnected(!net);await a.done();if(net){const x=q.getState_X(),y=q.getState_Y(),r=q.getState_Rotation()*Math.PI/180;if(!await eda.sch_PrimitiveWire.create([x,y,x+Math.round(Math.cos(r))*20,y+Math.round(Math.sin(r))*20],net))throw Error('Wire failed');}}}async function create(s){const c=await eda.sch_PrimitiveComponent.create(s.device,s.x,s.y,undefined,0,false,true,true);if(!c)throw Error('Create failed '+s.ref);if(!await eda.sch_PrimitiveComponent.modify(c,s.props))throw Error('Properties failed '+s.ref);await wire(c,s.pins);return c;}"""
def spec(ref,template,x,y,system=None,name=None):
    prop=copy.deepcopy(parts[template]['props']);uid=prop['Unique ID'] if ref==template else 'v12_'+ref
    props={'designator':ref,'uniqueId':uid,'name':name or prop['Name'],'addIntoBom':ref not in plan['dnp']}
    if not system:
        props.update(manufacturer=prop.get('Manufacturer',''),manufacturerId=prop.get('Manufacturer Part',''),supplier=prop.get('Supplier',''),supplierId=prop.get('Supplier Part',''))
    return {'ref':ref,'x':x,'y':y,'device':{'libraryUuid':LIB if system else PROJECT,'uuid':system or prop['Device']},'props':props,'pins':e[ref]}
pages={3:'a8fcac05b0a49c52',4:'8c8a42c355c95b77',5:'31c8ed08a1998d0d',7:'2eb77bba50a14eab',8:'61de9aff546f5073'}
replacements={3:[spec('U2','U2',700,900,'3e40b992cc4d452bb89d8a34a5cd3de2','ML307R-DL'),spec('R64','R64',1380,1140,'18db11499a04403ba8c98e2f7a687fbc','1k')],4:[spec('R55','R55',1400,1050,'b948db94476e4027ac8953235755ec96','10k'),spec('C55','C55',1650,1250,None,'33pF'),spec('C56','C84',1400,1250,None,'33pF'),spec('C57','C84',1150,1250,None,'33pF')],5:[],7:[spec('U10','U10',450,1080,'15713d554a62483087311b97659bdc17','SN74LVC1T45DCKR'),spec('U13','U8',950,1080,'15713d554a62483087311b97659bdc17','SN74LVC1T45DCKR'),spec('C71','C70',450,1360),spec('C72','C70',700,1360),spec('C73','C70',950,1360),spec('R77','R82',1200,1080,None,'100k'),spec('R78','R55',1200,1360,'b948db94476e4027ac8953235755ec96','10k')],8:[spec('U4','U4',430,530,'02135041ef0542b5aedac6e50ce8b9ed','AP63300WU-7'),spec('L1','L1',730,530,'ddf9e82fe6934dff9cb498d1772bbcd8','SWPA8040S6R8MT'),spec('C85','C80',1100,820)]}
rewire={3:['SW4','J7'],4:[],5:['J1','J2','J3'],7:[],8:[]}
notes={3:'V0.12 ML307R-DL：UART 1.8V；109脚逐脚核对，RSV均悬空。BOOT_MODE拉低后上电进入USB下载。',4:'V0.12：SIM_DET由VDD_EXT(1.8V)上拉10k；DATA/RST/CLK各33pF；LTE天线50Ω，主板U.FL接口。',5:'V0.12端子针序：RS485=P/A/B/G，RS232=P/T/R/G，TTL=P/T/R/G。P输入5~12V；T本板输出，R本板输入。',7:'V0.12：U10固定3.3V→1.8V发送；U13固定1.8V→3.3V接收；VDD_EXT关闭时双方高阻。无硬件流控。',8:'V0.12：LTE降压AP63300，3.8V；6.8uH电感；C80/C85两颗220uF储能。外部5V/2A下并发峰值须样板验证。'}
for page,uuid in pages.items():
    specs=replacements[page];replace=[s['ref'] for s in specs];removed=remove if page==7 else []
    refs=replace+removed+rewire[page]
    code=f"if((await eda.dmt_Project.getCurrentProjectInfo())?.uuid!=={js(PROJECT)})throw Error('Wrong V0.12 project');await eda.dmt_EditorControl.openDocument({js(uuid)});"+helpers
    code+='const specs='+js(specs)+';const refs='+js(refs)+';const parts=await eda.sch_PrimitiveComponent.getAll(\'part\');await clearAttached(parts.filter(c=>refs.includes(c.getState_Designator())||c.getState_Designator()?.startsWith(\'PROBE\')));'
    code+='for(const c of parts)if('+js(replace+removed)+'.includes(c.getState_Designator())||c.getState_Designator()?.startsWith(\'PROBE\'))if(!await eda.sch_PrimitiveComponent.delete(c))throw Error(\'Delete failed\');for(const s of specs)await create(s);'
    code+='const map='+js(e)+';for(const c of await eda.sch_PrimitiveComponent.getAll(\'part\'))if('+js(rewire[page])+'.includes(c.getState_Designator()))await wire(c,map[c.getState_Designator()]);'
    if page==3:code+=f"await eda.dmt_Schematic.modifySchematicPageName({js(uuid)},'03_ML307R_DL');"
    code+=f"await eda.sch_PrimitiveText.create(180,1600,{js(notes[page])},0,null,null,12);return {{saved:await eda.sch_Document.save(),refs:(await eda.sch_PrimitiveComponent.getAll('part')).map(c=>c.getState_Designator())}};"
    (P/f'scripts/revise-schematic-page{page}-v12.js').write_text(code,encoding='utf-8')
print('Prepared',len(e),'parts; replacements:',{p:[s['ref'] for s in a] for p,a in replacements.items()})
