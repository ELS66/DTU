from pathlib import Path
for p in Path('PCB/scripts').glob('*.js'):
 s=p.read_text(encoding='utf-8-sig')
 if 'importProjectByProjectFile' in s and p.name not in ['import-completed-project-v12.js','import-final-native-v12.js']:
  print(p.name,s[-750:])
