import json
from pathlib import Path
P=Path('PCB');guard=(P/'scripts/read-pcb-pads-v12.js').read_text().split('const out=')[0]
groups=[['SIM_DATA_M','SIM_RST_M','LTE_PWRKEY'],['232_RIN','LTE_RX_SER','MCU_LTE_PWRKEY'],['FIELD_TX','MCU_485_DE'],['SIM_DET','SIM_DATA']]
for i,nets in enumerate(groups,1):
 code=guard+"globalThis.dtuV12Repair={state:'running',batch:"+str(i)+",start:Date.now()};try{const result=await eda.pcb_Document.autoRouting({RoutingNets:"+json.dumps(nets)+",ignoreNets:['GND','LTE_ANT','LTE_RF_FEED','ESP_USB_DP','ESP_USB_DM','ESP_USB_DP_EXT','ESP_USB_DM_EXT','LTE_USB_DP','LTE_USB_DM','LTE_USB_DP_EXT','LTE_USB_DM_EXT'],layers:[1,2],cornerStyle:0,existingPrimitiveMode:'keep',optimization:1});globalThis.dtuV12Repair={state:'finished',batch:"+str(i)+",result};await eda.pcb_Document.save();return globalThis.dtuV12Repair;}catch(e){globalThis.dtuV12Repair={state:'failed',batch:"+str(i)+",error:String(e)};throw e;}"
 (P/f'scripts/native-repair-large-v12-{i}.js').write_text(code,encoding='utf8')
(P/'scripts/native-repair-status-large-v12.js').write_text(guard+'return globalThis.dtuV12Repair;',encoding='utf8')
code=guard+"const f=await eda.sys_FileManager.getProjectFile('DTU-V0.12-60x70-routing-stage',undefined,'epro2');if(!f)throw Error('No backup');return {name:f.name,size:f.size,bytes:Array.from(new Uint8Array(await f.arrayBuffer()))};"
(P/'scripts/export-stage-large-v12.js').write_text(code,encoding='utf8')
