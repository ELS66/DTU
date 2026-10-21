from pathlib import Path
import json,zipfile,shutil,hashlib,csv,sys
P=Path('PCB');E=P/'eda';M=P/'manifests';D=P/'docs'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
assert load(M/'hy20-final-pcb-drc-v13.json')['result']==[]
assert load(M/'hy20-final-actual-copper-check-v13.json')['conflicts']==[]
m=load(M/'hy20-manufacturing-check-v13.json');assert m['totalDrilledHoles']==320
s=(D/'V0.13-整体验收记录.md').read_text(encoding='utf-8-sig')
s=s.replace('已更新为布线优化版，过孔从 362 个减至 310 个，详见《V0.13-布线优化记录.md》。','已更新 HY2.0 立贴端子，过孔 304 个、总钻孔 320 个，详见《V0.13-HY2.0端子封装修正记录.md》。')
s=s.replace('J1/J2/J3 已由直针穿孔座改为 **JST S4B-PH-SM4-TB(LF)(SN)，C265102，PH2.0、4P、侧插贴片座**。','J1/J2/J3 已改为 **Megastar ZX-HY2.0-4PLT，C7429562，HY2.0、4P、立贴加盖座**。')
s=s.replace('三个底座朝下边缘插线，中心 X 为 16.5 / 30.0 / 43.5 mm，封装原点 Y 为 5.2 mm。塑料体约 11.9 mm 宽，座体相邻间隙约 1.6 mm；','三个底座位于下沿，从正面上方插入线端，中心 X 为 16.5 / 30.0 / 43.5 mm，封装原点 Y 为 5.0 mm，旋转 0°。塑料体约 12 mm 宽，座体相邻间隙约 1.5 mm，下沿距板边约 0.69 mm；')
s=s.replace('PTH 320 孔：298×0.2 mm 过孔、12×0.3 mm 过孔','PTH 314 孔：298×0.2 mm 过孔、6×0.3 mm 过孔').replace('合计 326 孔','合计 320 孔')
s=s.replace('S4B-PH-SM4-TB 的焊脚','ZX-HY2.0-4PLT 的焊脚')
s=s.replace('DTU-V0.13-60x70-routing-optimized.epro2','DTU-V0.13-60x70-HY20.epro2').replace('DTU-V0.13-60x70-routing-optimized-Gerber.zip','DTU-V0.13-60x70-HY20-Gerber.zip').replace('DTU-V0.13-60x70-布线优化资料包.zip','DTU-V0.13-60x70-HY20资料包.zip').replace('PCB/backups/20261015-before-routing-optimization/','PCB/backups/20261015-before-HY20-connector/').replace('优化前原件','端子修改前原件')
s=s.replace('DTU-V0.13-BOM-99.csv','DTU-V0.13-HY20-BOM-99.csv').replace('DTU-V0.13-CPL-99-Top.csv','DTU-V0.13-HY20-CPL-99-Top.csv')
s=s.replace('- JST PH 官方安装图：<https://www.jst-mfg.com/product/pdf/eng/ePH.pdf>（本地保存并渲染核对）。','- Megastar ZX-HY2.0-4PLT 厂家 Rev 2.0 图纸：`PCB/references/ZX-HY2.0-4PLT.pdf`；商品 <https://item.szlcsc.com/8427479.html>。')
(D/'V0.13-整体验收记录.md').write_text(s,encoding='utf8')
for n in ['V0.13-电路精简方案.md','V0.13-可选精简决策清单.md']:
 p=D/n;s=p.read_text(encoding='utf-8-sig').replace('C265102 正面焊接侧插贴片座','C7429562（ZX-HY2.0-4PLT）正面焊接立贴加盖座');p.write_text(s,encoding='utf8')
p=D/'V0.13-布线优化记录.md';s=p.read_text(encoding='utf-8-sig')
banner='> 历史记录：下文为端子修改前的布线优化结果。当前 HY2.0 版为 304 个过孔、320 个总钻孔，见《V0.13-HY2.0端子封装修正记录.md》。\n\n'
if banner not in s:s=banner+s
p.write_text(s,encoding='utf8')
(E/'DTU-V0.13-README.md').write_text('''# V0.13 HY2.0 立贴端子工程复核包

2026-10-15。60×70 mm，四层铜、单面装配；104 个封装，默认装配 99 件；304 个过孔、共 320 个钻孔。PCB DRC 0 项问题，原理图仍有 18 组警告。厂家 DFM 与首板测试尚未完成。

1. 嘉立创EDA打开 `DTU-V0.13-60x70-HY20.epro2`。
2. 厂家 DFM 上传 `DTU-V0.13-60x70-HY20-Gerber.zip`，不要上传整个资料包。内含 12 个生产文件，无重复过孔钻孔文件。
3. 装配使用 `DTU-V0.13-HY20-BOM-99.csv` 与 `DTU-V0.13-HY20-CPL-99-Top.csv`，均排除了 C50、C51、R32、J6、J7 五个 DNP。
4. J1/J2/J3 为指定的 ZX-HY2.0-4PLT / C7429562，HY2.0、4P、立贴加盖、正面 SMT。请按包内厂家图纸采购和核对替代型号，勿沿用旧 PH 侧插座。
5. 信号焊盘与固定片排中心距 3.0 mm；CPL 使用原生 Mid 坐标，三个端子 Mid Y=5.222 mm，封装原点 Ref Y=5.000 mm。
6. 阅读《V0.13-HY2.0端子封装修正记录.md》及《V0.13-整体验收记录.md》，保留其中厂家/首板待验证事项。
7. `HY20-Gerber-top.png` / `bottom.png` 是实际导出层预览，图中走线颜色是复核叠加效果。生产丝印仅保留接口名称/针序。以后自行导出须取消器件丝印/ComponentSilkscreen。
8. 旧通用工程、Gerber、验收包、BOM/CPL 链接已同步更新。端子修改前备份位于 `PCB/backups/20261015-before-HY20-connector/`。
''',encoding='utf8')
files=[E/'DTU-V0.13-60x70-HY20.epro2',E/'DTU-V0.13-60x70-HY20-Gerber.zip',E/'DTU-V0.13-HY20-BOM-99.csv',E/'DTU-V0.13-HY20-CPL-99-Top.csv',E/'DTU-V0.13-HY20-BOM-review.csv',E/'DTU-V0.13-HY20-Gerber-top.png',E/'DTU-V0.13-HY20-Gerber-bottom.png',D/'V0.13-HY2.0端子封装修正记录.md',D/'V0.13-整体验收记录.md',E/'DTU-V0.13-README.md',P/'references/ZX-HY2.0-4PLT.pdf']
target=E/'DTU-V0.13-60x70-HY20资料包.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:
  assert p.is_file() and p.stat().st_size>0
  z.write(p,p.name)
for path,count in [(target,len(files)),(E/'DTU-V0.13-60x70-HY20-Gerber.zip',12)]:
 with zipfile.ZipFile(path) as z:assert z.testzip() is None and len(z.namelist())==count
for a,b in [('DTU-V0.13-60x70-HY20.epro2','DTU-V0.13-60x70-DFM-review.epro2'),('DTU-V0.13-60x70-HY20-Gerber.zip','DTU-V0.13-60x70-SMT-4L-Gerber-DFM.zip'),('DTU-V0.13-60x70-HY20-Gerber-raw','DTU-V0.13-60x70-DFM-review'),('DTU-V0.13-60x70-HY20资料包.zip','DTU-V0.13-60x70-验收资料包.zip'),('DTU-V0.13-HY20-BOM-99.csv','DTU-V0.13-BOM-99.csv'),('DTU-V0.13-HY20-CPL-99-Top.csv','DTU-V0.13-CPL-99-Top.csv'),('DTU-V0.13-HY20-BOM-review.csv','DTU-V0.13-BOM-review.csv')]:shutil.copy2(E/a,E/b)
for layer in ['top','bottom','inner1','inner2']:shutil.copy2(E/f'DTU-V0.13-HY20-Gerber-{layer}.png',E/f'DTU-V0.13-Gerber-{layer}.png')
for a,b in [('hy20-final-routing-source-v13.json','final-connected-routing-v13.json'),('hy20-final-actual-copper-check-v13.json','final-copper-check-v13.json'),('hy20-final-pcb-drc-v13.json','check-pcb-v13.json'),('hy20-sch-drc-v13.json','check-sch-v13.json')]:shutil.copy2(M/a,M/b)
save(M/'final-gerber-dfm-check-v13.json',{'silkToMaskMinimumMm':m['topSilkMaskClearanceMm'],'holeToHoleMinimumMm':m['minimumDrillWallGapMm'],'allFourCopperLayersPresent':True,'topSmtConnectors':3,'factoryDfmPassed':False})
backup=P/'backups/20261015-before-HY20-connector'
save(backup/'backup-manifest.json',{'files':[{'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in backup.iterdir() if p.is_file() and p.name!='backup-manifest.json']})
save(M/'current-pcb-delivery-v13.json',{'revision':'V0.13 HY2.0 立贴端子修正 2026-10-15','boardMm':[60,70],'layers':4,'assembly':'Top','components':104,'defaultAssembly':99,'vias':304,'drilledHoles':320,'pcbDrcIssues':0,'schematicWarnings':18,'backupDirectory':str(backup.resolve()),'nativeProject':str((E/'DTU-V0.13-60x70-HY20.epro2').resolve()),'productionGerber':str((E/'DTU-V0.13-60x70-HY20-Gerber.zip').resolve()),'deliveryArchive':str(target.resolve()),'actualCopperManifest':'hy20-final-routing-source-v13.json','actualSourceSnapshot':'hy20-final-pcb-source-v13.json','connectors':{'model':'ZX-HY2.0-4PLT','supplierPart':'C7429562','signalFixedRowSpacingMm':3.0},'factoryDfmPassed':False,'files':[{'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]})
print(json.dumps({'package':str(target),'files':len(files),'bytes':target.stat().st_size,'gerberFiles':12,'pcbDrcIssues':0,'viaCount':304},ensure_ascii=True))
