from pathlib import Path
s=Path('PCB/docs/vendor/jlc-85160f4d0615e97e0ebf.js').read_text(encoding='utf-8-sig')
for pat in ['https://api.jlcpcb.com/','13:function','15:function']:
 i=s.find(pat);print(pat,s[max(0,i-100):i+1900])
s=Path('PCB/docs/vendor/jlc-d66cd4aa6d72db760a00.js').read_text(encoding='utf-8-sig')
for pat in ['Object(y.j)','Object(y.h)','Object(y.a)','calcTimeout','WebSocket']:
 i=s.find(pat);print(pat,s[max(0,i-150):i+700])
