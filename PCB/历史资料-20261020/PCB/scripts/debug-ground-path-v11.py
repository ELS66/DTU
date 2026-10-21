from pathlib import Path
s=Path('PCB/scripts/plan-interface-routing-v11.py').read_text();exec(s[:s.rindex('d=json.loads')]);pts=[(24.72436,14.86662),(24.72436,13),(25.4,12.3),(28.35,12.3),(28.35,11.85)];print([(a,b,LineString([a,b]).distance(obstacles('GND',1))) for a,b in zip(pts,pts[1:])])
