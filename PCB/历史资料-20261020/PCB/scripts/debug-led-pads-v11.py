from pathlib import Path
exec(Path('PCB/scripts/routing-geometry-v07.py').read_text().replace('routing-power-v07.json','routing-interface-v11.json').replace('pcb-pads-power-v07.json','pcb-pads-interface-v11.json'))
for p in pads:
 if p['net'] in ['LED_LTE_G_N','LED_LTE_B_N','LED_TX_N']:print(p['ref'],p['number'],p['net'],p['x'],p['y'],'bounds',p['geom'].bounds,'point inside',p['geom'].covers(Point(p['x'],p['y'])))
