import json
from pathlib import Path
p=Path('PCB'); n=json.loads((p/'reports/schematic-before-v05.net').read_text(encoding='utf-8')); cs={c['props']['Designator']:c for c in n['components'].values()}
map={r:{k:v['net'] for k,v in c['pinInfoMap'].items() if v.get('net')} for r,c in cs.items()}
remove6=['U9','U13','Q7','R104','R108','R109','R110','R114','R115','R116','R125','R126','R127','R128','R129','R130','R131','C103','C104']
remove7=['Q4','R77','R78','R79','R80','R81','R83','R86','R87','C71']
remove2=['R17','R18'];remove3=['R62','R63']
removed=remove6+remove7+remove2+remove3
for r in removed:map.pop(r,None)
renames={'MODE_TTL_N':'TTL_PRESENT_N','MODE232_N':'RS232_PRESENT_N','MODE485_N':'RS485_PRESENT_N','TTL_VREF':'IF_VREF','RS232_VREF':'IF_VREF','RS485_VREF':'IF_VREF'}
for r,pins in map.items():
 for k,v in list(pins.items()):pins[k]=renames.get(v,v)
map['U10']={'1':'LTE_STATUS_N','2':'MCU_LTE_TX','3':'MCU_LTE_RX','4':'GND','5':'LTE_TX_SER','6':'LTE_RX_SER','7':'LTE_STATUS_N','8':'VDD_3V3'}
for pin in ['16','22','23']:map['U2'].pop(pin,None)
map['C110']={'1':'IF_VREF','2':'GND'}
map['J6']={'1':'GND','2':'ESP_USB_DP_EXT','3':'ESP_USB_DM_EXT','4':'ESP_EN','5':'ESP_BOOT'}
map['J7']={'1':'GND','2':'LTE_USB_DP_EXT','3':'LTE_USB_DM_EXT','4':'LTE_USB_VBUS','5':'LTE_BOOT_SOURCE'}
leds=[('ESP_R',4,2,'red'),('ESP_G',17,4,'green'),('ESP_B',16,5,'blue'),('LTE_R',9,7,'red'),('LTE_G',11,9,'green'),('LTE_B',26,25,'blue'),('TX',25,11,'green'),('RX',24,12,'blue')]
for i,(name,pin,gpio,color) in enumerate(leds):
 net='LED_'+name+'_N';map['U1'][str(pin)]=net;map['D'+str(30+i)]={'1':net,'2':'LED_'+name+'_A'};map['R'+str(140+i)]={'1':'VDD_3V3','2':'LED_'+name+'_A'}
plan={'version':'V0.5','removed':removed,'removeByPage':{'2':remove2,'3':remove3,'6':remove6,'7':remove7},'expected':map,'leds':[{'name':name,'pin':str(pin),'gpio':gpio,'color':color,'diode':'D'+str(30+i),'resistor':'R'+str(140+i),'activeLow':True} for i,(name,pin,gpio,color) in enumerate(leds)],'dnp':['J6','J7','C50','C51','C55'],'beforeCount':len(cs),'plannedCount':len(cs)-len(removed)+17,'mode':'Exactly one powered interface; no multi-source priority or interlock'}
(p/'manifests/revision-v05.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
base='if((await eda.dmt_Project.getCurrentProjectInfo())?.uuid!=="b7122aadd3e496b681150192bfbef370394a2ba91164cb1621df30a137bdfaf5")throw Error("Wrong project");'
pages={'2':'905678d5aaed7ed3','3':'a8fcac05b0a49c52','5':'31c8ed08a1998d0d','6':'8902a3019bd8d84c','7':'2eb77bba50a14eab'}
wire='''for(const c of parts){const ref=c.getState_Designator();if(!refs.includes(ref))continue;for(const q of await c.getAllPins()){const net=map[ref]?.[q.getState_PinNumber()];const a=q.toAsync();a.setState_NoConnected(!net);await a.done();if(!net)continue;const x=q.getState_X(),y=q.getState_Y(),r=q.getState_Rotation();if(!await eda.sch_PrimitiveWire.create([x,y,x+Math.round(Math.cos(r*Math.PI/180))*20,y+Math.round(Math.sin(r*Math.PI/180))*20],net))throw Error("Wire failed "+ref+":"+q.getState_PinNumber());}}'''
clear='''const parts=await eda.sch_PrimitiveComponent.getAll("part");const wires=await eda.sch_PrimitiveWire.getAll();const ids=new Set();for(const c of parts){if(!refs.includes(c.getState_Designator())&&!remove.includes(c.getState_Designator()))continue;for(const q of await c.getAllPins()){const x=q.getState_X(),y=q.getState_Y();for(const w of wires){const line=w.getState_Line();const paths=Array.isArray(line[0])?line:[line];if(paths.some(p=>{for(let i=0;i<p.length;i+=2)if(Math.abs(p[i]-x)<.001&&Math.abs(p[i+1]-y)<.001)return true;return false;}))ids.add(w.getState_PrimitiveId());}}}if(ids.size&&!await eda.sch_PrimitiveWire.delete([...ids]))throw Error("Wire removal failed");for(const c of parts)if(remove.includes(c.getState_Designator())&&!await eda.sch_PrimitiveComponent.delete(c.getState_PrimitiveId()))throw Error("Part removal failed");'''
refs6=[r for r,c in cs.items() if c['props'].get('Channel ID','').startswith('$6') and r not in remove6]+['C110']
createcap='''let cap=(await eda.sch_PrimitiveComponent.getAll("part")).find(c=>c.getState_Designator()==="C110");if(!cap){cap=await eda.sch_PrimitiveComponent.create({libraryUuid:"0819f05c4eef4c71ace90d822a990e87",uuid:"96b39256cc3f4d80bd3b503deb4f3328"},750,1050,undefined,0,false,true,true);if(!cap)throw Error("Reference cap failed");const a=cap.toAsync();a.setState_Designator("C110");await a.done();}'''
s=base+f'await eda.dmt_EditorControl.openDocument("{pages["6"]}");'+createcap+'const refs='+json.dumps(refs6)+';const remove='+json.dumps(remove6)+';const map='+json.dumps(map)+';'+clear+wire+'return {saved:await eda.sch_Document.save(),removed:remove,remaining:(await eda.sch_PrimitiveComponent.getAll("part")).length};'
(p/'scripts/revise-selector-v05.js').write_text(s,encoding='utf-8')
for page,refs,rm in [('5',['U6','U7','U8','U12'],[]),('2',['U1'],[]),('3',['U2'],[])]:
 s=base+f'await eda.dmt_EditorControl.openDocument("{pages[page]}");const refs='+json.dumps(refs)+';const remove='+json.dumps(rm)+';const map='+json.dumps(map)+';'+clear+wire+'return {saved:await eda.sch_Document.save(),reconnected:refs};'
 (p/f'scripts/revise-page-{page}-v05.js').write_text(s,encoding='utf-8')
refs7=[r for r,c in cs.items() if c['props'].get('Channel ID','').startswith('$7') and r not in remove7 and r!='U10']
s=base+f'await eda.dmt_EditorControl.openDocument("{pages["7"]}");'+'const refs='+json.dumps(refs7+['U10','U10_NEW'])+';const remove='+json.dumps(remove7+['U10'])+';const map='+json.dumps(map)+';'+'''const before=await eda.sch_PrimitiveComponent.getAll("part");const old=before.find(c=>c.getState_Designator()==="U10");const neo=before.find(c=>c.getState_Designator()==="U10_NEW");if(!old||!neo)throw Error("Missing buffer pair");const uid=old.getState_UniqueId();'''+clear+'''const a=neo.toAsync();a.setState_Designator("U10");a.setState_UniqueId(uid);await a.done();const live=await eda.sch_PrimitiveComponent.getAll("part");'''+wire.replace('of parts','of live')+'return {saved:await eda.sch_Document.save(),removed:remove,buffer:neo.getState_Component()};'
(p/'scripts/revise-lte-control-v05.js').write_text(s,encoding='utf-8')
print(json.dumps({'plannedCount':plan['plannedCount'],'removed':len(removed),'selectorResistorsBefore':32,'selectorResistorsAfter':18,'resistorsAfterWithLEDs':71,'LEDGPIO':plan['leds']}))

