from pathlib import Path
import json,hashlib,os,csv,re

root=Path('D:/DTU'); pcb=root/'PCB'; final=pcb/'V0.14.4-最终资料'; history=pcb/'历史资料-20261020'
plan=json.loads((history/'归档迁移计划.json').read_text(encoding='utf-8'))
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
for f in plan['files']+plan['copyFiles']:
 p=Path(f['destination']);assert p.is_file() and p.stat().st_size==f['bytes'] and sha(p)==f['sha256'],str(p)
for l in plan['junctions']:
 p=Path(l['destination']);assert p.is_junction() and str(p.resolve())==l['target'],str(p)
manifest=plan['oldDeliveryManifest'].copy()
def finalpath(rel):return str(final/rel)
manifest.update({
 'organizedDate':'2026-10-20',
 'deliveryDirectory':str(final),
 'historyDirectory':str(history),
 'nativeProject':finalpath('01-工程/DTU-V0.14.4-60x75-Threefix.epro2'),
 'editableNativeProject':finalpath('01-工程/DTU-V0.14.4-三处修正-60x75.eprj2'),
 'productionGerber':finalpath('02-制造基准/DTU-V0.14.4-60x75-Threefix-Gerber.zip'),
 'baselineBom':finalpath('02-制造基准/DTU-V0.14.4-Threefix-BOM-99.csv'),
 'coordinates':finalpath('02-制造基准/DTU-V0.14.4-Threefix-CPL-99-Top.csv'),
 'procurementBom':finalpath('03-本次采购/DTU-V0.14.4-BOM-本次采购验证版-20261020.xlsx'),
 'procurementOrder':finalpath('03-本次采购/订单数据-20261020.xlsx'),
 'procurementBomStatus':'本次采购验证版，橙灯用于本次验证，下次恢复红色；尺寸与首板验证项见工作簿。',
 'actualCopperManifest':finalpath('04-验证资料/threefix-actual-routing-v14_4.json'),
 'actualSourceSnapshot':finalpath('04-验证资料/threefix-reopened-source-v14_4.json'),
 'mountKeepoutVerification':finalpath('04-验证资料/mountfix-verification-v14_1.json'),
 'pinLandVerification':finalpath('04-验证资料/threefix-verification-v14_4.json'),
 'J5ManufacturerReview':finalpath('04-验证资料/threefix-J5-manufacturer-review-v14_4.json'),
 'pcbGeometryChangedDuringOrganization':False,
 'legacyReviewArchive':str(history/'PCB/eda/DTU-V0.14.4-60x75-天线座与电阻阵列复查包.zip'),
 'backupDirectory':str(history/'PCB/backups/20261016-before-antenna-array-fix-162422'),
 'files':[{'file':str(Path(f['destination']).relative_to(final)).replace('\\','/'),'bytes':f['bytes'],'sha256':f['sha256']} for f in plan['copyFiles']]
})
manifest.pop('deliveryArchive',None)
(pcb/'manifests').mkdir()
data=json.dumps(manifest,ensure_ascii=False,indent=2)+'\n'
(pcb/'manifests/current-pcb-delivery.json').write_text(data,encoding='utf-8')
(final/'资料索引.json').write_text(data,encoding='utf-8')
(final/'00-资料说明.md').write_text('''# DTU V0.14.4 资料说明

整理日期：2026-10-20。PCB基线为2026-10-16的Threefix，60×75mm、4层、正面贴装，板上104个器件实例，默认装配99件。此次仅整理文件与入口，没有修改PCB、焊盘、走线或Gerber。

## 从哪里开始

| 目录 | 内容与用途 |
|---|---|
| [01-工程](01-工程/) | `.epro2`为本轮制造文件对应的导出基线；`.eprj2`为同轮可编辑本地工程。工程中的物料标注保留原设计基准。 |
| [02-制造基准](02-制造基准/) | 原Gerber ZIP、原99件设计BOM、正面贴装坐标。这里的原BOM用于对照工程，采购按下一目录。 |
| [03-本次采购](03-本次采购/) | 2026-10-20采购验证BOM、订单原表及核对记录。BOM首页保留“物料类型、完整型号、封装、数量”，数量是单板用量；第二页有位号、5板用量、采购只数和待核对项。 |
| [04-验证资料](04-验证资料/) | 安装孔、引脚边界、J5与排阻等复核记录，实际导出快照及DRC记录。 |

最新采购BOM：[本次采购验证版](03-本次采购/DTU-V0.14.4-BOM-本次采购验证版-20261020.xlsx)。原理图/PCB与采购替料的差别保留在工作簿中，不要把原基准BOM直接当成更新后的采购清单。

## 本轮装配决定

- U1采购ESP32-C5-WROOM-1U-N8R8，软件按实际内存配置；原工程物料标注为N8R4。
- U2采购并实际装配ML307R-DL。在DFM暂时排除U2只是检查操作。
- D30/D33本次使用橙色19-217/S2C-AL1M2VY/3T验证，下次恢复红色。
- U6采购SP3485EN-L/TR，首板验证供电和RS485通信。
- U4采购SCT2330TVBR，仍需验证启动、纹波、LTE发射负载突变和温升。
- 通用PH2.0插座、国产射频座、通用排阻的尺寸或内部连接，以及部分替换品牌TVS的来料/数据表仍需核对。具体项目见BOM第二页。

## 验证状态

保存重开及原生PCB DRC记录为0项。工厂DFM尚未记为全部通过，部分采购替料尚待实物或首板验证。因此“最终资料”表示本轮归集后的版本基线，不表示所有制造和替料验证已完成。

## 历史资料与查找

历史文件统一存于[历史资料-20261020](../历史资料-20261020/)。原目录层级保留在其中的`PCB/`和`outputs/`下。目录内的[文件迁移清单](../历史资料-20261020/文件迁移清单.csv)提供原路径、新路径、字节数及SHA-256。

共用器件手册和模型仍放在[参考资料](../references/)，嘉立创EDA连接服务环境保留在原处。

[资料索引](资料索引.json)记录当前文件路径、哈希和关键状态。迁移后的入口清单位于`PCB/manifests/current-pcb-delivery.json`。
''',encoding='utf-8')
(history/'README.md').write_text(f'''# 硬件历史资料

归档日期：2026-10-20。保留原目录层级，不删除旧版本和过程记录。

- `PCB/eda/`：旧工程、各轮导出和原扁平目录快照，包含被复制到最终目录的V0.14.4原文件。
- `PCB/native-*/`：各轮本地工程与自动备份。
- `PCB/backups/`：修改前备份。
- `PCB/reports/`、`PCB/manifests/`：历史报告、快照、旧入口及检查记录。
- `PCB/docs/`、`PCB/scripts/`：历史设计说明、分阶段脚本。脚本中的旧路径是历史记录，不应直接批量重放。
- `outputs/`：旧BOM、降本候选、采购审校和生成工具。原文件及两个依赖目录链接完整保留，未展开复制其外部目标。

共归档{len(plan['files'])}个普通文件、{len(plan['junctions'])}个目录链接。普通文件迁移后逐一核对字节数和SHA-256。

[文件迁移清单](文件迁移清单.csv)可按原文件名或原路径查找；[迁移计划](归档迁移计划.json)保留完整映射和迁移前入口；[执行记录](已执行操作.ndjson)记录复制及移动动作。

当前工作资料请使用[最终资料入口](../V0.14.4-最终资料/00-资料说明.md)。不要用归档中的“current”文件名判断最新版本。
''',encoding='utf-8')
(pcb/'README.md').write_text('''# DTU 硬件资料

当前硬件基线为 **V0.14.4，60×75mm、4层、正面99件装配**。文件已于2026-10-20整理。

- [最终资料入口与使用说明](V0.14.4-最终资料/00-资料说明.md)
- [本次采购验证BOM](V0.14.4-最终资料/03-本次采购/DTU-V0.14.4-BOM-本次采购验证版-20261020.xlsx)
- [工程文件](V0.14.4-最终资料/01-工程/)
- [Gerber、设计基准BOM与贴装坐标](V0.14.4-最终资料/02-制造基准/)
- [验证记录](V0.14.4-最终资料/04-验证资料/)
- [历史资料统一归档](历史资料-20261020/README.md)
- [共用器件手册和模型](references/)

本次采购使用U1 N8R8、ML307R-DL和已确认的橙色指示灯。尺寸待核项及SCT2330等首板验证要求保留在采购BOM第二页。工厂DFM未标记全部通过。

程序入口清单为[当前资料索引](manifests/current-pcb-delivery.json)。旧V0.11/V0.12首页和设计规范已经收入历史目录，不再作为当前选型依据。
''',encoding='utf-8')
(pcb/'DTU主板硬件设计与API绘板规范.md').write_text('''# DTU 当前硬件资料入口

当前版本为V0.14.4。本文件保留原入口路径，避免继续把旧V0.11设计规范作为当前规范。

请先阅读[本轮资料说明](V0.14.4-最终资料/00-资料说明.md)，再查阅[工程](V0.14.4-最终资料/01-工程/)、[制造基准](V0.14.4-最终资料/02-制造基准/)与[本次采购BOM](V0.14.4-最终资料/03-本次采购/DTU-V0.14.4-BOM-本次采购验证版-20261020.xlsx)。

原详细规范完整保留于[历史文件](历史资料-20261020/PCB/DTU主板硬件设计与API绘板规范.md)，其中旧主控内存、蜂窝模组、尺寸等描述不能代替当前工程和BOM。
''',encoding='utf-8')
(root/'outputs/README.md').write_text('''# 输出资料位置

硬件BOM与历史输出已于2026-10-20归整：

- [当前V0.14.4资料](../PCB/V0.14.4-最终资料/00-资料说明.md)
- [最新采购BOM](../PCB/V0.14.4-最终资料/03-本次采购/DTU-V0.14.4-BOM-本次采购验证版-20261020.xlsx)
- [历史输出目录](../PCB/历史资料-20261020/outputs/)
''',encoding='utf-8')
readme=root/'README.md';text=readme.read_text(encoding='utf-8-sig')
needle='## 当前交付\n'
text=text.replace(needle,needle+'\n- [硬件 V0.14.4 最终资料与历史归档](PCB/README.md)。\n',1)
readme.write_text(text,encoding='utf-8')
assert not manifest['factoryDfmPassed'] and manifest['U2AssemblyStillRequired']
for key in ['nativeProject','editableNativeProject','productionGerber','baselineBom','coordinates','procurementBom','procurementOrder','actualCopperManifest','actualSourceSnapshot','mountKeepoutVerification','pinLandVerification','J5ManufacturerReview','legacyReviewArchive','backupDirectory']:
 assert Path(manifest[key]).exists(),key
# Check Markdown links in the new entry documents.
for md in [pcb/'README.md',pcb/'DTU主板硬件设计与API绘板规范.md',final/'00-资料说明.md',history/'README.md',root/'outputs/README.md']:
 for link in re.findall(r'\]\(([^)]+)\)',md.read_text(encoding='utf-8')):
  if not link.startswith(('https:','http:','#')):assert (md.parent/link).exists(),(str(md),link)
result={'date':'2026-10-20','historicalFilesVerified':len(plan['files']),'finalFilesVerified':len(plan['copyFiles']),'junctionsPreserved':len(plan['junctions']),'hashMismatches':0,'missingFiles':0,'pcbGeometryChanged':False,'factoryDfmPassed':manifest['factoryDfmPassed'],'finalDirectory':str(final),'historyDirectory':str(history)}
(final/'整理校验结果.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
