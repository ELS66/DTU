from pathlib import Path
import json,zipfile,hashlib,shutil,copy
R=Path('PCB');M=R/'manifests';E=R/'eda';D=R/'docs'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
stage=load(M/'mountfix-plan-v14_1.json');report=load(M/'mountfix-verification-v14_1.json');reopen=load(M/'mountfix-reopen-verification-v14_1.json');previous=stage['baseline']
assert report['nativeDrcIssues']==0 and report['maximumRegionCenterErrorMm']<.00001 and len(report['regionToHoleCenterChecks'])==8 and reopen['reopenVerified']
assert len(report['holesUnchanged'])==4 and len(report['unchangedProductionFilesByBytes'])==10
for kind,old in [('BOM-99','DTU-V0.14-Clearancefix-BOM-99.csv'),('CPL-99-Top','DTU-V0.14-Clearancefix-CPL-99-Top.csv')]:shutil.copy2(E/old,E/f'DTU-V0.14.1-Mountfix-{kind}.csv')
readme=E/'DTU-V0.14.1-Mountfix-README.md';doc=D/'V0.14.1-安装孔禁铜错位修正记录.md'
readme.write_text('''# DTU V0.14.1 · 安装孔禁铜错位修正

日期：2026-10-16。板子仍为60×75 mm、四层、正面贴装，99件默认实装。

V0.14增高板子时，上方两个安装孔已移到y=71 mm，但L2、L3内铜的对应禁铜圆区仍停在y=66 mm，造成错位。本版已将这四个禁铜区上移5 mm，与安装孔中心对齐，并重建铺铜。

四个Ø3.2 mm非金属化孔的位置保持：(4,4)、(56,4)、(4,71)、(56,71) mm，坐标原点在板子左下角。对应禁铜圆区标称半径3.4 mm，两内层共8处全部与孔中心对齐。旧位置的多余空圈已恢复铺铜。

实际导出检查通过：原生DRC=0；只有两份内层铜Gerber发生改变，其余10份制造文件与V0.14保持字节一致；BOM、贴装坐标、孔位、器件、走线与原理图保持。工程关闭后重新打开，禁铜修正仍保留。

请使用本包的Gerber整包复查。工程内部保留V0.14系列标题，本次修补文件以V0.14.1标识。此前整板装配模型、工厂DFM与阻抗等待复核项继续保留，详见随包记录；本次未宣称整板工厂DFM通过。
''',encoding='utf8')
inner=[q for q in report['actualFourLayerCopperClearances'] if q['layer'] in report['changedProductionFiles']]
doc.write_text(f'''# V0.14.1 安装孔禁铜错位修正记录

日期：2026-10-16。修改前备份：`{stage['backupDirectory']}`。

## 原因与修正

V0.14调整板高时，两个上方安装孔从y=66移到了y=71 mm，L2、L3上四个对应禁铜区没有同步移动。实际导出内铜在孔附近仅留下钻孔自身的避让，另外在旧坐标出现空圈。这是上版工程修改的遗漏。

本次移动四个禁铜区5 mm，并重建三块铺铜。原理图、封装、器件位置、走线、过孔、孔径、孔位均保持；下方四处内层禁铜区保持。生产文件只改变Gerber_InnerLayer1.G1与Gerber_InnerLayer2.G2，其余10份制造文件校验后沿用原字节。

## 实际核对

|项目|结果|
|---|---|
|板框|60×75 mm|
|四个安装孔|Ø3.2 mm NPTH；(4,4)、(56,4)、(4,71)、(56,71) mm|
|孔中心与两内层禁铜中心|8/8对应，误差小于0.00001 mm|
|禁铜区标称半径|3.4 mm|
|两内层最小孔中心至铜距离|{min(q['centerToCopperMm'] for q in inner):.4f} mm|
|两内层最小孔壁至铜距离|{min(q['holeWallToCopperMm'] for q in inner):.4f} mm|
|旧坐标空圈|四处均已恢复铺铜|
|重新打开工程|禁铜位置保持|
|原生PCB DRC|0|
|钻孔/过孔|326/310，保持|
|实装BOM/CPL|99件，保持|

对比图中的蓝圈为源文件禁铜圆边界，红十字为实际钻孔中心。铺铜的孤岛去除可能使孔旁极窄的边角铜被移除，禁铜区中心与孔中心已重合。图底分别显示左上、右上两处，背景为实际导出的L2铜；L3已完成同样检查。

新增核对规则：每个安装孔必须在L2、L3分别找到一个同心、半径3.4 mm的禁铜区；导出后再次量测四层铜至每个孔的距离。后续改变板框或孔位时继续执行这项检查。

本次检查没有替代工厂DFM。V0.14中SIM座、天线座及部分灯的模型边界、历史装配余量、阻抗与硬件验证等待复核事项，继续保留在随包的上一版记录中。
''',encoding='utf8')
files=[E/'DTU-V0.14.1-60x75-Mountfix.epro2',E/'DTU-V0.14.1-60x75-Mountfix-Gerber.zip',E/'DTU-V0.14.1-Mountfix-BOM-99.csv',E/'DTU-V0.14.1-Mountfix-CPL-99-Top.csv',readme,doc,E/'DTU-V0.14.1-Mountfix-before-after.png']
manifest=copy.deepcopy(previous);manifest.update({'revision':'V0.14.1 安装孔禁铜错位修正 2026-10-16','backupDirectory':stage['backupDirectory'],'nativeProject':str(files[0].resolve()),'productionGerber':str(files[1].resolve()),'deliveryArchive':str((E/'DTU-V0.14.1-60x75-安装孔修正复查包.zip').resolve()),'actualSourceSnapshot':'mountfix-source-v14_1.json','mountKeepoutVerification':'mountfix-verification-v14_1.json','factoryDfmPassed':False,'files':[{'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]})
save(M/'current-pcb-delivery-v14_1.json',manifest)
extras={'安装孔核对结果.json':M/'mountfix-verification-v14_1.json','重新打开核对.json':M/'mountfix-reopen-verification-v14_1.json','版本清单.json':M/'current-pcb-delivery-v14_1.json','V0.14其他电路待复核.json':M/'clearancefix-dfm-pending-items-v14.json','V0.14其他电路复核记录.md':D/'V0.14-封装边界与模组净空修正记录.md'}
bundle=Path(manifest['deliveryArchive'])
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,p.name)
 for name,p in extras.items():z.write(p,name)
with zipfile.ZipFile(bundle) as z:
 assert z.testzip() is None
 for p in files:assert z.read(p.name)==p.read_bytes()
for name in ['current-pcb-delivery.json','current-pcb-delivery-v13.json','current-pcb-delivery-v14.json']:save(M/name,manifest)
for p,name in [(files[0],'DTU-current.epro2'),(files[1],'DTU-current-Gerber.zip'),(files[2],'DTU-current-BOM.csv'),(files[3],'DTU-current-CPL-Top.csv'),(bundle,'DTU-current-review.zip')]:shutil.copy2(p,E/name)
(E/'当前版本说明.md').write_text('当前版本：V0.14.1，60×75 mm，四层、单面贴装。\n\n本版修正上方安装孔与两内层禁铜区错位。请使用 DTU-V0.14.1-60x75-安装孔修正复查包.zip 或 DTU-current-review.zip 整包复查。旧V0.14及V0.13文件保留追溯。工厂DFM待复核项见包内记录。\n',encoding='utf8')
print('Verified patch archive:',bundle,'entries',len(files)+len(extras),'bytes',bundle.stat().st_size)
