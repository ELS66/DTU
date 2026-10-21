from pathlib import Path
import json,zipfile,shutil,hashlib
P=Path('PCB');E=P/'eda';M=P/'manifests';D=P/'docs'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
check=load(M/'npth-export-verification-v13.json');assert load(M/'npth-fixed-pcb-drc-v13.json')['result']==[]
assert check['changedPrimitiveCount']==4 and check['totalDrillHoles']==322
backup=Path(load(M/'npth-backup-path-v13.json')['directory'])
report=f'''# V0.13 四角无铜安装孔修正记录

2026-10-15。用户定位到四角安装孔的“焊盘孔环”危险提示后，本次仅修正这四个孔的定义及对应生产图形。

## 已确认原因

四个安装孔原本已设置 plated=false，钻孔约 3.200001 mm，但默认焊盘外径 126 mil 导出了 3.2004 mm 的铜圆盘。每孔在四个铜层均有此图形，名义单边孔环仅约 0.0002 mm，与用户所示位置和危险规则相符。安装孔为非金属化机械孔，不应保留这样的焊环。

## 已完成修改

- 四孔中心仍为 (4,4)、(56,4)、(4,66)、(56,66) mm；孔径仍为 Ø3.2 mm，保留非金属化属性。
- 原生工程将这四个孔的焊盘尺寸设为 0；软件在存储/导出时会钳位成约 0.001 mm 的最小占位盘。该占位盘全部落在钻孔内部，未形成孔外铜环。
- 交付的生产 Gerber 额外移除四个孔内、四铜层共 16 个 0.001 mm 占位铜点，得到不含这些铜图形的安装孔；保留全部钻孔和阻焊开窗。此处理只针对已核实的四孔坐标及占位尺寸，没有过滤其他孔或改动其他铜图形。
- 顶底阻焊开窗约 Ø3.4 mm；四层铜在孔边外的最小净空约 0.9 mm。
- 未移动器件或改变任何电气走线/过孔；原生源码逐项比对只有四个独立安装孔 PAD 发生变化。306 个电气过孔、104 个封装/99 件实装保持不变。

## 导出核对

- 原生 PCB DRC：0 项问题。
- PTH 316 孔，NPTH 6 孔，总计 322 孔；NPTH 包含四个 Ø3.2 mm 安装孔及两个 SIM 定位孔。
- 清理后四个铜层无安装孔铜圆盘或孔外残留孔环；对应 16 处铜净空逐层验证。
- 板框、安装孔中心、孔距、孔径保持原设计；BOM/CPL 与 SMTfix 版完全一致。
- 生产 ZIP 保留 12 个文件，未重复放入独立过孔钻孔文件；ZIP 完整性已检查。

## 文件与后续

用于重新运行嘉立创 DFM 的文件为 `DTU-V0.13-60x70-NPTHfix-Gerber.zip`。请使用这个已经清理并验证的生产 ZIP。原始导出 `NPTHfix-Gerber-raw` 保留供追溯；以后从原生工程自行重新导出时，也应按 `verify-npth-export-v13.py` 清理软件产生的四孔内部占位铜点。

原生工程为 `DTU-V0.13-60x70-NPTHfix.epro2`；完整复查包为 `DTU-V0.13-60x70-安装孔修正复查包.zip`。

本次修正尚未在用户的嘉立创 DFM 中重新验证，不宣称四项危险已经清零。此前普通过孔 0.125 mm 孔环与截图中 0.15 mm 黄色阈值的差异、同位号端子模型提示及其余加工检查仍待复核；没有调整或屏蔽检查阈值。

修改前备份：`{backup}`。
'''
rep=D/'V0.13-四角无铜安装孔修正记录.md';rep.write_text(report,encoding='utf8')
readme=E/'DTU-V0.13-NPTHfix-README.md';readme.write_text('''# V0.13 四角安装孔修正复查包

当前版：60×70 mm、四层铜、单面装配，104 个封装/99 件默认实装，306 个电气过孔、322 个总钻孔。原生 PCB DRC=0，完整厂家 DFM 尚未完成。

请上传 `DTU-V0.13-60x70-NPTHfix-Gerber.zip` 重新检查“焊盘孔环”。此 ZIP 已移除四角无铜安装孔的多余铜图形，保留 Ø3.2 mm 孔径和原位置，含 12 个生产文件。

需要装配检查时使用包内 NPTHfix-BOM-99.csv / NPTHfix-CPL-99-Top.csv；它们与前一 SMTfix 版内容相同。

阅读《V0.13-四角无铜安装孔修正记录.md》。原生工程自行导出可能产生极小孔内占位铜点，请依记录处理，不要混用旧的 HY20/SMTfix Gerber。
''',encoding='utf8')
for a,b in [('DTU-V0.13-SMTfix-BOM-99.csv','DTU-V0.13-NPTHfix-BOM-99.csv'),('DTU-V0.13-SMTfix-CPL-99-Top.csv','DTU-V0.13-NPTHfix-CPL-99-Top.csv')]:shutil.copy2(E/a,E/b)
files=[E/'DTU-V0.13-60x70-NPTHfix.epro2',E/'DTU-V0.13-60x70-NPTHfix-Gerber.zip',E/'DTU-V0.13-NPTHfix-BOM-99.csv',E/'DTU-V0.13-NPTHfix-CPL-99-Top.csv',rep,readme]
package=E/'DTU-V0.13-60x70-安装孔修正复查包.zip'
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:
  assert p.is_file() and p.stat().st_size>0
  z.write(p,p.name)
for p in [files[0],files[1],package]:
 with zipfile.ZipFile(p) as z:assert z.testzip() is None
old=load(M/'current-pcb-delivery-v13.json')
old.update({'revision':'V0.13 四角安装孔修正 2026-10-15','status':'DFM复查中，四角安装孔待重新运行DFM确认','nativeProject':str(files[0].resolve()),'productionGerber':str(files[1].resolve()),'deliveryArchive':str(package.resolve()),'actualSourceSnapshot':'npth-four-pad-fix-v13.json','backupDirectory':str(backup),'files':[{'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]})
old['openDfmItems']=[s for s in old.get('openDfmItems',[]) if not s.startswith('4项孔环危险')]+['四角安装孔已去除残留铜环，待新Gerber重新运行DFM确认']
save(M/'current-pcb-delivery-v13.json',old)
shutil.copy2(M/'npth-fixed-pcb-drc-v13.json',M/'check-pcb-v13.json')
for a,b in [('DTU-V0.13-60x70-NPTHfix.epro2','DTU-V0.13-60x70-DFM-review.epro2'),('DTU-V0.13-60x70-NPTHfix-Gerber.zip','DTU-V0.13-60x70-SMT-4L-Gerber-DFM.zip'),('DTU-V0.13-60x70-安装孔修正复查包.zip','DTU-V0.13-60x70-验收资料包.zip'),('DTU-V0.13-NPTHfix-README.md','DTU-V0.13-README.md')]:shutil.copy2(E/a,E/b)
accept=D/'V0.13-整体验收记录.md';s=accept.read_text(encoding='utf8');banner='> 安装孔修正更新：当前 NPTHfix 版已去除四角安装孔残留铜环，孔径/位置不变；待重新运行厂家 DFM 确认。生产文件以《V0.13-四角无铜安装孔修正记录.md》及 current-pcb-delivery-v13.json 为准。\n\n'
if banner not in s:
 shutil.copy2(accept,backup/accept.name)
 accept.write_text(banner+s,encoding='utf8')
print(json.dumps({'package':str(package),'productionGerber':str(files[1]),'bytes':package.stat().st_size,'files':len(files),'pcbDrcIssues':0,'NPTH':check['NPTH'],'mounts':check['mounts']},ensure_ascii=True))
