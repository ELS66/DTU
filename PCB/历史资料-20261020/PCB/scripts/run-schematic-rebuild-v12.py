import importlib.util,json
from pathlib import Path
loader=importlib.util.spec_from_file_location('bridge',Path(__file__).with_name('eda-v12.py'));m=importlib.util.module_from_spec(loader);loader.loader.exec_module(m)
for page in [4,7,8]:
    for action in ['activate','rebuild']:
        name=f'{action}-schematic-page{page}-v12.js'
        r=m.run((m.ROOT/'scripts'/name).read_text(encoding='utf-8'),f'reports/{action}-page{page}-v12.json')
        print(action,page,json.dumps(r,ensure_ascii=True),flush=True)
r=m.run((m.ROOT/'scripts/export-schematic-before-v12.js').read_text(), 'manifests/schematic-after-v12.json')
print('Exported',len(r['content']),flush=True)
