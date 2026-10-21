from pathlib import Path
P=Path('PCB/scripts');s=(P/'replan-power-repair-large-v12.py').read_text(encoding='utf-8')
s=s.replace(".replace('routing-power-large-v12.json','routing-resume-large-v12.json')",".replace('routing-power-large-v12.json','routing-pass2-large-v12.json').replace('step=.1;nx=601;ny=701','layers=[1,2,15,16];step=.1;nx=601;ny=701')")
s=s.replace('escape-ripup-large-v12','pass3-ripup-large-v12').replace('complete-repair-large-v12','pass3-repair-large-v12').replace('escape-fanout-large-v12','pass3-fanout-large-v12')
s=s.replace("load_plan(P/'manifests/local-repair-large-v12.json');",'')
s=s.replace("Point(x,y).distance(Point(v['x'],v['y']))+.225<=v['diameter']/2+.01","Point(x,y).distance(Point(v['x'],v['y']))<.12")
(P/'replan-pass3-power-v12.py').write_text(s,encoding='utf-8')
