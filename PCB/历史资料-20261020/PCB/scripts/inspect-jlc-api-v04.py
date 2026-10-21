from pathlib import Path
import re,sys
sys.stdout.reconfigure(encoding='utf-8');s=Path('PCB/docs/vendor/jlc-d66cd4aa6d72db760a00.js').read_text(encoding='utf-8-sig');i=s.index('calc:function');print(s[i:i+7000]);print('function exports',s[:3500])
for p in Path('PCB/docs/vendor').glob('jlc-*.js'):
 st=p.read_text(encoding='utf-8-sig')
 for m in re.finditer(r'https?[^"\s]{0,100}(?:api|jlcpcb)[^"\s]{0,100}',st):
  v=m.group()
  if 'jlcpcb.com'in v and ('api'in v or 'base'in v):print(p.name,v[:170])
