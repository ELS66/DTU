from pathlib import Path
import json,zipfile,shutil,hashlib
R=Path('PCB');M=R/'manifests';E=R/'eda';D=R/'docs'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
v=load(M/'silkholefix-manufacturing-verification-v13.json');backup=load(M/'silkholefix-backup-v13.json')['directory']
for suffix in ['BOM-99.csv','CPL-99-Top.csv']:
 src=E/f'DTU-V0.13-Silkclean-{suffix}';dest=E/f'DTU-V0.13-Silkholefix-{suffix}';shutil.copy2(src,dest);assert src.read_bytes()==dest.read_bytes()
guide=D/'V0.13-精简丝印版接口说明.md'
report=D/'V0.13-丝印避孔修正记录.md'
report.write_text(f'''# V0.13 丝印避孔修正记录

2026-10-16。用户提供嘉立创DFM“丝印距孔”截图：顶层8红、2黄，RS485的B字旁小过孔被标出，显示约0.03/0.05/0.12 mm。上一 Silkclean 版检查了丝印到阻焊开窗，却漏查盖油过孔的钻孔壁；盖油不等于这项丝印距孔检查可以省略。不得将本项与丝印距焊盘合并判断。

在修改前完整备份，目录：{backup}。

定位到坐标约(17.5,9.0) mm、直径0.2 mm过孔。前版精确导出几何测量B字到孔壁最近约0.0283 mm，吻合截图0.03 mm；DFM多项可能对应同一字的不同笔画，不能直接当作多个不同过孔。

本版在可编辑工程修改5个STRING对象：RS485的P/A/B/G整行上移0.80 mm，保持X坐标分别13.5/15.5/17.5/19.5 mm，与焊脚水平对齐；RS485名称左移0.80 mm、上移0.95 mm。其他两组文字保持原位，保留原有15个文本、1.8 mm名义字号和0.15 mm笔画宽度。

重新保存、关闭、打开核对一致。原生PCB DRC为0项。已对新Gerber全部322个钻孔（含盖油过孔、下载孔、SIM孔及安装孔）的实际孔壁和全部保留丝印几何计算间距：最小{v['silkToDrillWallMinimumGapMm']:.6f} mm；小于0.18 mm的孔/丝印组合为0。到阻焊开窗的最小间距为{v['silkToMaskMinimumGapMm']:.6f} mm。两项均超过用户截图良好阈值0.18 mm。端子区图形已按真实导出笔画与孔位渲染检查。

新旧PCB源及整套工程有效记录逐项比较，只有5个文本的X/Y坐标变化。非丝印原生Gerber/钻孔几何也与前版核对（容差0.00001 mm，沿用此前确认的安装孔占位和盖油数值残点过滤）。生产ZIP中的10个非丝印文件从前版按字节原样保留，只替换顶/底丝印。器件、铜线、过孔、焊盘、阻焊、钢网、板框和针序不变。BOM/CPL原样复制，104个封装/99件默认实装、60×70 mm、4层单面贴装规格不变。

本地几何核对和PCB DRC不等于整板厂家DFM通过。请使用DTU-V0.13-60x70-Silkholefix-Gerber.zip重新运行“丝印距孔”“丝印距焊盘”及原有其他待确认检查；厂家检查状态仍为未完成。保留旧版文件便于回溯。
''',encoding='utf8')
readme=E/'DTU-V0.13-Silkholefix-README.md'
readme.write_text('''# V0.13 丝印避孔复查版

当前版本为Silkholefix。使用配套Silkholefix-Gerber.zip复查DFM，可编辑工程为Silkholefix.epro2。

RS485的四个针序字母整体上移，名称向左上避孔，针序仍为P/A/B/G。其余为RS232和UART，针序P/T/R/G。

核对全部322个钻孔，丝印到孔壁最小约0.262 mm，到阻焊开窗最小约0.289 mm；原生PCB DRC为0。整板厂家DFM仍待复查。

仅5个文本位置变化。铜线、孔位、焊盘、非丝印生产图层和BOM/CPL与Silkclean前版一致。具体修正、备份路径及局限见配套记录。下载针序、元件极性识别见接口说明。
''',encoding='utf8')
items=[E/'DTU-V0.13-60x70-Silkholefix.epro2',E/'DTU-V0.13-60x70-Silkholefix-Gerber.zip',E/'DTU-V0.13-Silkholefix-BOM-99.csv',E/'DTU-V0.13-Silkholefix-CPL-99-Top.csv',guide,report,readme,M/'silkholefix-manufacturing-verification-v13.json',E/'DTU-V0.13-Silkholefix-terminal-detail.png']
package=E/'DTU-V0.13-60x70-丝印避孔修正复查包.zip'
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
 for p in items:z.write(p,p.name)
for p in [items[0],items[1],package]:
 with zipfile.ZipFile(p) as z:assert z.testzip() is None
current=load(M/'current-pcb-delivery-v13.json')
current.update({'revision':'V0.13 丝印避孔修正 2026-10-16','status':'RS485文字已避开盖油过孔，待厂家DFM重新检查丝印距孔及其他待确认项','backupDirectory':backup,'nativeProject':str(items[0].resolve()),'productionGerber':str(items[1].resolve()),'deliveryArchive':str(package.resolve()),'actualSourceSnapshot':'silkholefix-reopened-source-v13.json','silkscreenReview':str(report.resolve()),'silkscreenVerification':'silkholefix-manufacturing-verification-v13.json','factoryDfmPassed':False,'files':[{'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in items]})
current['openDfmItems']=[s for s in current['openDfmItems'] if not s.startswith('丝印')]+['丝印：RS485整组文字已避孔；全部322孔检查，丝印距孔最小0.262mm、距开窗0.289mm，待厂家DFM重跑确认。']
save(M/'current-pcb-delivery-v13.json',current)
shutil.copy2(M/'silkholefix-pcb-drc-v13.json',M/'check-pcb-v13.json')
for a,b in [('DTU-V0.13-60x70-Silkholefix.epro2','DTU-V0.13-60x70-DFM-review.epro2'),('DTU-V0.13-60x70-Silkholefix-Gerber.zip','DTU-V0.13-60x70-SMT-4L-Gerber-DFM.zip'),(package.name,'DTU-V0.13-60x70-验收资料包.zip'),(readme.name,'DTU-V0.13-README.md')]:shutil.copy2(E/a,E/b)
print(json.dumps({'project':str(items[0]),'gerber':str(items[1]),'package':str(package),'backup':backup},ensure_ascii=True))
