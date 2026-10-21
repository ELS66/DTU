from pathlib import Path
p=Path('PCB/scripts/plan-fanout-v07.py');s=p.read_text(encoding='utf-8-sig');s=s[:s.index('railnames=')];Path('PCB/scripts/routing-geometry-v07.py').write_text(s,encoding='utf-8')
