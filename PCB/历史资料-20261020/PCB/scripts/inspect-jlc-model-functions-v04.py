from pathlib import Path
import re
s=Path('PCB/docs/vendor/jlc-d66cd4aa6d72db760a00.js').read_text(encoding='utf-8-sig')
for pat in ['function I','I=','getImpedanceConfigCopperTrace','getCoverlayValuesByConfig','getW2ValueByConfig']:
 for m in list(re.finditer(re.escape(pat),s))[:2]:print(pat,s[max(0,m.start()-60):m.end()+1500])
import json
j=json.loads(Path('PCB/docs/vendor/jlc-impedance-models.json').read_text(encoding='utf-8-sig'))
for m in j['body']['list']:print(m['layerNumber'],m['impedancePattern'],m['impedanceType'],m['impedancePictureAccessId'])
