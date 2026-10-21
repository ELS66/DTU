from pathlib import Path
p=Path('PCB/scripts/plan-fanout-v07.py');s=p.read_text(encoding='utf-8-sig');a=s.index('def obstacles(');b=s.index('for net in sorted(railnames',a);g=Path('PCB/scripts/routing-geometry-v07.py');g.write_text(g.read_text(encoding='utf-8')+s[a:b],encoding='utf-8')
