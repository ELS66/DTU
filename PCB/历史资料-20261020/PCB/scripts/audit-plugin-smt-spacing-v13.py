"""Read-only PCB audit of download-hole to top SMT pad distances."""
from pathlib import Path
import csv
import json

root = Path('PCB')
exec((root / 'scripts/router-v13.py').read_text(encoding='utf8').replace(
    'read-pcb-pads-v13.json', 'smt-fixed-pcb-pads-v13.json'))

through = [q for q in pads if q['layer'] == 12]
surface = [q for q in pads if q['layer'] == 1]
assert {q['ref'] for q in through} == {'J6', 'J7'}
rows = []
for a in through:
    for b in surface:
        distance = a['geom'].distance(b['geom'])
        if distance < 3.05:
            rows.append({'download': a['ref'], 'pin': a['number'],
                         'smt': b['ref'], 'smtPin': b['number'],
                         'gapMm': distance,
                         'severity': '危险' if distance < 2.03 else '警告',
                         'downloadPadId': a['id'], 'smtPadId': b['id']})
rows.sort(key=lambda r: r['gapMm'])
danger = sum(r['gapMm'] < 2.03 for r in rows)
warning = len(rows) - danger
assert (danger, warning) == (21, 22)
assembly_files = [root / 'eda/DTU-V0.13-NPTHfix-BOM-99.csv',
                  root / 'eda/DTU-V0.13-NPTHfix-CPL-99-Top.csv']
for file in assembly_files:
    with file.open(encoding='utf-8-sig', newline='') as f:
        for row in csv.reader(f):
            for cell in row:
                refs = cell.replace(';', ',').replace(' ', ',').split(',')
                assert 'J6' not in refs and 'J7' not in refs

result = {
    'PCBModified': False, 'factoryDfmPassed': False,
    'source': 'smt-fixed-pcb-pads-v13.json; NPTHfix BOM/CPL; 用户截图及 DFM 界面说明',
    'dangerCount': danger, 'warningCount': warning,
    'minimumCopperPadGapMm': rows[0]['gapMm'],
    'allPluginPadsAreJ6J7': True, 'J6J7AbsentFromDefaultBOMandCPL': True,
    'decision': '默认裸孔、不装排针、不安排插件焊接，此项焊接治具间距规则不适用；保留记录。',
    'fixtureAccess': '下载探针及定位治具未定型，仍需按实际针头和定位结构验证，不能以本项判定治具已通过。',
    'pairs': rows,
}
(root / 'manifests/dfm-plugin-smt-spacing-v13.json').write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
with (root / 'reports/V0.13-下载孔与贴片间距复核.csv').open(
        'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

doc = root / 'docs/V0.13-下载裸孔装配间距复核.md'
doc.write_text('''# V0.13 下载裸孔装配间距复核

2026-10-15。当前 60×70 mm、四层、单面装配版本。此轮没有修改工程、铜层、阻焊、钢网和 DFM 阈值，生产文件保持 NPTHfix 版本。

用户截图为“插件焊盘距贴片焊盘”，软件说明明确用于预警插件焊接治具的开制空间，危险阈值 2.03 mm、警告上限 3.05 mm。它不同于铜间距防短路检查，也不同于下载探针治具机械验收。

按当前焊盘唯一 ID 和实际几何计算，得到 21 项小于 2.03 mm、22 项为 2.03～3.05 mm，与截图统计完全一致。这 43 项的插件侧全部为顶部两组下载孔 J6/J7，没有其他插件器件混入。最小距离约 0.714 mm，为 J7/2 至 D20/2；其次 J6/2 至 D18/2 约 0.715 mm。截图显示精度与源几何有轻微取整差异。完整逐项结果见对应 CSV 和 JSON。

已核对当前实装 BOM 与 CPL：J6/J7 均未列入默认 99 件实装。生产装配条件为：J6/J7 保留两组各 5 个裸焊孔，不装排针，不焊接，不安排这些孔的插件过炉；下载时使用外部接触工具。该条件与用户已确定方案一致。

处理结论：本项按默认装配条件登记为插件焊接治具规则不适用，保留布局和原始报警记录，不为消除颜色搬移 USB 保护、天线座或电容。没有调低规则阈值，也没有宣称整板 DFM 通过。未来若加装排针、连接器或安排插件焊接，必须重新评估器件本体、烙铁/喷嘴/焊接治具空间和工艺。

下载针头、定位板及治具外形尚未定型。本轮铜焊盘距离只能用于定位报警，不能证明所有实际下载治具都能装入；使用前按实际针头和定位结构验证接触及避让。

依据：DFM 当前界面说明；`smt-fixed-pcb-pads-v13.json`；`DTU-V0.13-NPTHfix-BOM-99.csv`；`DTU-V0.13-NPTHfix-CPL-99-Top.csv`。可复现脚本为 `audit-plugin-smt-spacing-v13.py`。插件焊接工艺参考：https://www.jlc.com/portal/q7i49023.html 。
''', encoding='utf8')
manifest_path = root / 'manifests/current-pcb-delivery-v13.json'
manifest = json.loads(manifest_path.read_text(encoding='utf8'))
manifest['downloadHoleAssemblyReview'] = str(doc.resolve())
manifest['dfmDispositionNotes'] = [
    note for note in manifest.get('dfmDispositionNotes', [])
    if not note.startswith('插件焊盘距贴片焊盘')
] + ['插件焊盘距贴片焊盘21红22黄全部定位至J6/J7；默认裸孔不装不焊，按装配条件不适用；加装排针须重审。']
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf8')
print(json.dumps({k: v for k, v in result.items() if k != 'pairs'}, ensure_ascii=True))
