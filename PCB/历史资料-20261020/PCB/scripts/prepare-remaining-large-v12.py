from pathlib import Path
P=Path('PCB/scripts')
s=(P/'load-native-routing-v12.py').read_text(encoding='utf-8-sig')
s=s.split('# Preserve existing ground reference')[0]
s=s.replace("exec(Path('PCB/scripts/router-v12.py').read_text().replace('pcb-pads-routing-v12.json','pcb-pads-current-v12.json'))","exec(Path('PCB/scripts/router-large-v12.py').read_text(encoding='utf8'))")
s=s.replace('step=.1;nx=501;ny=601','step=.1;nx=601;ny=701').replace('routing-current-full-v12.json','routing-power-large-v12.json')
s+="\nbase_obstacles=obstacles\ndef obstacles(net,layer,ignore=()):\n g=base_obstacles(net,layer,ignore)\n if layer==16 and net!='GND':g=unary_union([g,box(16.4,54.8,24,61.5),box(27.3,38.0,35,43.4)])\n return g\n"
(P/'load-native-routing-large-v12.py').write_text(s,encoding='utf8')
s=(P/'plan-remaining-routing-v12.py').read_text().replace('load-native-routing-v12.py','load-native-routing-large-v12.py').replace('remaining-routing-v12','remaining-routing-large-v12')
# Limit redundant search of impossible channels; failures are inspected and repaired separately.
s=s.replace('sorted(choices)[:12]','sorted(choices)[:6]')
(P/'plan-remaining-routing-large-v12.py').write_text(s,encoding='utf8')
