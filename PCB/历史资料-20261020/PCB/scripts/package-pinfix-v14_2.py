"""Package verified pin-land revision and actual exported copper comparisons."""
from pathlib import Path
import json,zipfile,copy,shutil,hashlib,math
R=Path('PCB');M=R/'manifests';E=R/'eda';D=R/'docs'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
stage=load(M/'pinfix-plan-v14_2.json');report=load(M/'pinfix-verification-v14_2.json');old=stage['baseline']
s=(R/'scripts/package-silkclean-v13.py').read_text(encoding='utf8');exec(s[s.index('def rows('):s.index('before=rows(')])
before=rows(load(M/'pinfix-after-source-v14_2.json')['result']['source']);after=rows(load(M/'pinfix-reopened-source-v14_2.json')['result']['source'])
maxdelta=0
def compare(a,b):
 global maxdelta
 if isinstance(a,(int,float)) and not isinstance(a,bool) and isinstance(b,(int,float)) and not isinstance(b,bool):
  maxdelta=max(maxdelta,abs(a-b));assert abs(a-b)<1e-9;return
 if isinstance(a,dict):
  assert a.keys()==b.keys()
  for k in a:compare(a[k],b[k])
 elif isinstance(a,list):
  assert len(a)==len(b)
  for aa,bb in zip(a,b):compare(aa,bb)
 else:assert a==b
compare(before,after)
assert report['nativeDrcIssues']==0 and report['targetModelCount']==170 and report['unchangedPasteVerified']
report['reopenedSourceVerified']=True;report['maximumReopenSerializationDeltaMil']=maxdelta
save(M/'pinfix-verification-v14_2.json',report)
for name in ['BOM-99','CPL-99-Top']:
 shutil.copy2(E/f'DTU-V0.14.1-Mountfix-{name}.csv',E/f'DTU-V0.14.2-Pinfix-{name}.csv')
readme=E/'DTU-V0.14.2-Pinfix-README.md';doc=D/'V0.14.2-引脚边界修正记录.md'
readme.write_text('''# DTU V0.14.2 引脚边界修正

2026-10-16。基于 V0.14.1，60×75 mm、四层、正面贴装、99件默认实装。

本次修正 ESP32 U1、SIM 座 J4 和五颗同封装 LED 的标称引脚模型与铜面边界不匹配。修改49个封装焊盘定义，共影响57个板上焊盘；SIM_CLK 一条走线局部避让。保留全部真实引脚模型，原始钢网开口保持几何一致。

实际导出的铜面已逐个核对 U1、U2、J4、D30、D31、D33、D34、D36 的170个引脚模型，全部有铜面支撑。原生 DRC=0，重开工程后修改保留。安装孔及两内层8个禁铜区对应正确，BOM/CPL、钻孔、器件位置保持。

请用本版工程和 Gerber 整包重新执行工厂 SMT DFM；旧版本历史文件仍保留。内部工程标题保留 V0.14 系列名称，以本文件版本为准。

尚未宣称工厂 DFM 全过：天线座 J5 的可焊/悬空接触模型、HY2.0 座同编号模型碰撞、实际装配公差及工艺审核仍需核实。此版未通过删除模型或改变检测阈值消除报警。
''',encoding='utf8')
doc.write_text(f'''# V0.14.2 引脚边界修正记录

备份：`{stage['backupDirectory']}`。

U1 对照乐鑫 ESP32-C5-WROOM-1U 数据手册 v1.3 图10-2、11-2，原标称侧焊盘1.5×0.9 mm、中心焊盘1.3 mm。库中引脚与焊盘宽度名义相等且存在小于0.0001 mm的坐标差。本版采用工程加宽，每边增加0.020 mm，保留物理模型。此为本项目工程余量，并非厂家发布的新推荐尺寸。

J4 对照讯普 SMN-303 尺寸图，保留原引脚模型、原外端位置与钢网开口，将七个信号焊盘向根部延伸0.13 mm。原模型约0.122 mm超出铜面的部分得到支撑。SIM_CLK 邻近的三处折线坐标向内调整0.04 mm，避免延伸铜面导致间距不足。最小模型铜面余量约0.0079 mm，只代表标称几何支撑，不能等同于覆盖全部实际装配公差。

D30/D31/D33/D34/D36共用封装，保留物理模型，焊盘每边增加0.020 mm，处理模型边缘超出铜面的微小偏差。

49个主封装PAD记录修改，新增49个显式钢网FILL记录以保留实际旧版开口；板上实际影响57焊盘。所有引脚编号、PAD_NET、原理图、BOM、器件坐标及方向保持。U2的109焊盘及模型不变，重新确认实际导出铜面包含全部109个模型。57个变更焊盘至异网焊盘、过孔、走线按0.152 mm阈值检查无新增不足；原生PCB DRC为0。钢网开口几何、底层铜、两内层铜、钻孔、板框、丝印等10份制造文件的几何与V0.14.1一致。

关闭再重开工程后源数据复核通过，浮点重序列化最大差值{maxdelta:.3g} mil。4个Ø3.2 mm NPTH与L2/L3共8个半径3.4 mm禁铜区仍同心。310过孔、326钻孔保持。

复核引脚模型170个：U1=40，U2=109，J4=11，5颗LED=10。实际导出铜面全部包含对应标称模型。U1最小余量约0.01994 mm，J4约0.00792 mm，LED约0.01660 mm，U2约0.04994 mm。模型多边形的标称几何检查不替代厂家公差、贴装和工厂DFM。

待复核：J5天线座接触区是否含绝缘体覆盖/悬空金属，需要准确型号的可焊区定义，未盲目向射频座下扩铜；HY2.0座同编号模型自碰撞识别及其他装配报警仍需工厂复查。原生DRC=0与本地170项包含检查不代表全部SMT DFM报警归零。

参考：[乐鑫原厂数据手册](https://documentation.espressif.com/esp32-c5-wroom-1_wroom-1u_datasheet_en.pdf)，[讯普SMN-303原厂尺寸图（分销商托管）](https://static.chipdip.ru/lib/978/DOC012978119.pdf)。
''',encoding='utf8')
# Create focused comparisons from actual production copper, with unchanged nominal model outlines.
exec((R/'scripts/render-hy20-gerber-v13.py').read_text(encoding='utf8').split('for label,copper,mask,silk in')[0])
from shapely.affinity import rotate,translate
cs=load(M/'clearancefix-final-pads-v14.json')['result'];by={c['ref']:c for c in cs}
def plane(path):
 global z
 z.close();z=zipfile.ZipFile(path);cache.clear();return unary_union([g for g,d in geom('Gerber_TopLayer.GTL')[0] if d])
oldplane=plane(old['productionGerber']);newplane=plane(E/'DTU-V0.14.2-60x75-Pinfix-Gerber.zip')
src=(R/'scripts/package-silkclean-v13.py').read_text(encoding='utf8');exec(src[src.index('def active_project('):src.index('oldproj=active_project(')])
a=active_project(E/'DTU-V0.14.2-60x75-Pinfix.epro2')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',21);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
im=Image.new('RGB',(1280,950),'#f5f6f5');d=ImageDraw.Draw(im)
windows=[('U1',(40.15,50.95,42.55,53.25)),('J4',(20.35,29.25,22.15,31.85))]
for row,(ref,win) in enumerate(windows):
 for col,(label,planegeom) in enumerate([('V0.14.1',oldplane),('V0.14.2',newplane)]):
  x0=col*640+25;y0=row*455+55;xb,yb,xe,ye=win;scale=min(580/(xe-xb),365/(ye-yb));xx=lambda x,y:(x0+(x-xb)*scale,y0+(ye-y)*scale)
  d.rectangle([x0,y0,x0+580,y0+365],fill='#162b28')
  draw_geom(d,planegeom.intersection(box(*win)),'#d6ba6e',xx)
  c=by[ref]
  for k,q in a.items():
   if k[:2]!=('FOOTPRINT',c['footprint']['uuid']) or q.get('layerId')!=50 or 'path' not in q:continue
   for p in q['path']:
    v=[v*.0254 for v in p if isinstance(v,(int,float))];g=Polygon(list(zip(v[::2],v[1::2])));g=translate(rotate(g,c['rotation'],origin=(0,0)),c['x']*.0254,c['y']*.0254)
    lines=g.boundary.intersection(box(*win))
    for ln in list(lines.geoms) if hasattr(lines,'geoms') else [lines]:
     if not ln.is_empty and hasattr(ln,'coords'):d.line([xx(x,y) for x,y in ln.coords],fill='#28e9ec',width=1)
  d.text((x0,y0-30),f'{ref} / {label}',font=font,fill='#182d29')
d.text((25,913),'Gold: actual copper   Cyan: unchanged nominal lead model   Local geometry check; factory DFM pending.',font=small,fill='#182d29')
preview=E/'DTU-V0.14.2-Pinfix-before-after.png';im.save(preview)
files=[E/'DTU-V0.14.2-60x75-Pinfix.epro2',E/'DTU-V0.14.2-60x75-Pinfix-Gerber.zip',E/'DTU-V0.14.2-Pinfix-BOM-99.csv',E/'DTU-V0.14.2-Pinfix-CPL-99-Top.csv',readme,doc,preview]
bundle=E/'DTU-V0.14.2-60x75-引脚边界修正复查包.zip'
manifest=copy.deepcopy(old);manifest.update({'revision':'V0.14.2 引脚边界修正 2026-10-16','backupDirectory':stage['backupDirectory'],'projectUuid':'2c279e5e44ab838a0da4374e7618123ceb24be898b3f9279a35d7ed197648b6b','nativeProject':str(files[0].resolve()),'productionGerber':str(files[1].resolve()),'deliveryArchive':str(bundle.resolve()),'actualCopperManifest':'pinfix-actual-routing-v14_2.json','actualSourceSnapshot':'pinfix-reopened-source-v14_2.json','pinLandVerification':'pinfix-verification-v14_2.json','factoryDfmPassed':False,'files':[{'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]})
save(M/'current-pcb-delivery-v14_2.json',manifest)
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as zz:
 for p in files:zz.write(p,p.name)
 for name,p in [('核对结果.json',M/'pinfix-verification-v14_2.json'),('版本清单.json',M/'current-pcb-delivery-v14_2.json')]:zz.write(p,name)
with zipfile.ZipFile(bundle) as zz:
 assert zz.testzip() is None
 for p in files:assert zz.read(p.name)==p.read_bytes()
for name in ['current-pcb-delivery.json','current-pcb-delivery-v13.json','current-pcb-delivery-v14.json']:save(M/name,manifest)
for p,n in [(files[0],'DTU-current.epro2'),(files[1],'DTU-current-Gerber.zip'),(files[2],'DTU-current-BOM.csv'),(files[3],'DTU-current-CPL-Top.csv'),(bundle,'DTU-current-review.zip')]:shutil.copy2(p,E/n)
(E/'当前版本说明.md').write_text('当前版本：V0.14.2，60×75 mm，四层、单面贴装。\n\n引脚边界工程修正。请使用 DTU-V0.14.2-60x75-引脚边界修正复查包.zip；旧版保留追溯。工厂完整SMT DFM尚待复核，详见包内记录。\n',encoding='utf8')
print('Packaged',bundle,'reopen max delta',maxdelta,'bytes',bundle.stat().st_size)
