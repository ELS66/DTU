from pathlib import Path
s=Path('PCB/docs/vendor/jlc-d66cd4aa6d72db760a00.js').read_text(encoding='utf-8-sig')
i=s.index('function I');j=s.index('function ',i+15);print(s[j-650:j+200]);i=s.index('getImpedanceConfigCopperTraceWidtList:function');print(s[i:i+1100]);i=s.index('getImpedanceConfigCoverlayList:function');print(s[i:i+950])
