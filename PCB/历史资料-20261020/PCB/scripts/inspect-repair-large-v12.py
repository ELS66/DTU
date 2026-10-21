from pathlib import Path
code=Path('PCB/scripts/load-native-routing-large-v12.py').read_text(encoding='utf-8-sig').replace('routing-power-large-v12.json','routing-resume-large-v12.json')
exec(code)
exec(Path('PCB/scripts/plan-remaining-routing-large-v12.py').read_text(encoding='utf-8-sig').split("power={")[0].split("def groups(net):")[1].join(['def groups(net):','']))
for net in ['SIM_DATA_M','SIM_RST_M','LTE_PWRKEY','232_RIN','LTE_RX_SER','MCU_LTE_PWRKEY','FIELD_TX','MCU_485_DE','SIM_DET','SIM_DATA']:
 print('\n',net,'groups',groups(net),flush=True)
 print('pads',[(p['ref'],p['number'],p['layer'],round(p['x'],3),round(p['y'],3),p['geom'].bounds) for p in pads if p['net']==net])
print('counts',len(native['polys']),len(native['vias']))
