from pathlib import Path
p=Path('PCB/scripts/prepare-pcb-layout-v04.py');s=p.read_text(encoding='utf-8-sig');s=s.replace("'U11':(18,12.5,0)","'U11':(55.4,56,0)").replace("'L3':(13,17.8,0)","'L3':(55.4,61,180)").replace("'U6':(8.5,11.7,0)","'D14':(52.1,55,90),'U6':(8.5,11.7,0)").replace("'J4':(8,28,270)","'J4':(8.12,28,270)")
s=s.replace("for ref in ['C107','C108','C109','R92','R93']:pt[ref]=pinpoint('U11','3')", "pt['C107']=pinpoint('L3','1');pt['C108']=pinpoint('D14','1')\nfor ref in ['C109','R92','R93']:pt[ref]=pinpoint('U11','3')")
p.write_text(s,encoding='utf-8')
