from pathlib import Path
P=Path('PCB/scripts');old='be907e0c26ece4ccdedd2f5b24e25f76812bc6b957961675838d5450e3220cbc';new='fd71bf4d415315427fd7a027a4dd7e0a77d66de0d184ebd89693182b3f596907'
for name in ['read-pcb-pads-v12','read-routing-v12','read-source-v12','check-drc-v12','check-schematic-v12','export-schematic-raw-v12','export-schematic-preview-v12','export-gerber-large-v12','export-cpl-large-v12','capture-top-large-v12','capture-bottom-large-v12','activate-pcb-v12']:
 s=(P/(name+'.js')).read_text(encoding='utf-8-sig').replace(old,new);(P/('final-'+name+'.js')).write_text(s,encoding='utf-8')
s=(P/'export-stage-large-v12.js').read_text(encoding='utf-8').replace(old,new).replace('DTU-V0.12-60x70-routing-stage','DTU-V0.12-ML307R-DL-60x70')
(P/'export-final-native-v12.js').write_text(s,encoding='utf-8')
