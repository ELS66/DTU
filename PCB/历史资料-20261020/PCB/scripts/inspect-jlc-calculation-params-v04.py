from pathlib import Path
import re,sys
sys.stdout.reconfigure(encoding='utf-8');s=Path('PCB/docs/vendor/jlc-d66cd4aa6d72db760a00.js').read_text(encoding='utf-8-sig')
for pat in ['calcImpedance','calculateImpedance','calc:function','calc:','calculate:','startCalc','calculate:function','calcResult','calcType','f.call','impedanceValue','impedanceCalc']:
 hits=list(re.finditer(re.escape(pat),s));print('PATTERN',pat,'count',len(hits))
 for m in hits[:3]:print(s[max(0,m.start()-130):m.end()+1100])
