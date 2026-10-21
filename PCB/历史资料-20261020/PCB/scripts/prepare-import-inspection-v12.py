from pathlib import Path
s=Path('PCB/scripts/import-completed-project-v12.js').read_text(encoding='utf-8');s=s.split('const info=')[0]+"globalThis.dtuV12FinalFile=f;return await eda.sys_FileManager.extractProjectInfo(f);"
Path('PCB/scripts/inspect-completed-project-v12.js').write_text(s,encoding='utf-8')
