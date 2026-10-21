from pathlib import Path
import json,zipfile,copy,shutil,hashlib,sys
sys.path.insert(0,str(Path('PCB/.tools').resolve()))
R=Path('PCB');M=R/'manifests';E=R/'eda';D=R/'docs'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
stage=load(M/'threefix-plan-v14_4.json');report=load(M/'threefix-verification-v14_4.json');j5=load(M/'threefix-J5-manufacturer-review-v14_4.json');old=stage['baseline']
s=(R/'scripts/package-silkclean-v13.py').read_text(encoding='utf8');exec(s[s.index('def rows('):s.index('before=rows(')])
a=rows(load(M/'threefix-after-source-v14_4.json')['result']['source']);b=rows(load(M/'threefix-reopened-source-v14_4.json')['result']['source']);maximum=0
def same(a,b):
 global maximum
 if isinstance(a,(int,float)) and not isinstance(a,bool) and isinstance(b,(int,float)) and not isinstance(b,bool):maximum=max(maximum,abs(a-b));assert abs(a-b)<1e-9
 elif isinstance(a,dict):
  assert a.keys()==b.keys()
  for k in a:same(a[k],b[k])
 elif isinstance(a,list):
  assert len(a)==len(b)
  for x,y in zip(a,b):same(x,y)
 else:assert a==b
same(a,b)
assert report['nativeDrcIssues']==0 and report['targetModelCount']==186 and j5['manufacturerNoTraceAreaTopCopperAreaMm2']==0
report['reopenedSourceVerified']=True;report['maximumReopenSerializationDeltaMil']=maximum;report['U2PcbAndAssemblyUnchanged']=True
report['preservedProductionGeometries'].remove('Gerber_TopPasteMaskLayer.GTP');report['oneJ5PasteApertureTranslationVerified']=True
report['pending']='Factory DFM recheck required. J5 whole-model overlap can remain flagged because internal insulation-covered metal is included; U2 remains populated in production and its previously documented model difference is retained.'
save(M/'threefix-verification-v14_4.json',report)
for suffix in ['BOM-99.csv','CPL-99-Top.csv']:shutil.copy2(E/f'DTU-V0.14.2-Pinfix-{suffix}',E/f'DTU-V0.14.4-Threefix-{suffix}')
readme=E/'DTU-V0.14.4-Threefix-README.md';doc=D/'V0.14.4-天线座与电阻阵列复核记录.md'
readme.write_text('''# DTU V0.14.4 · 天线座与电阻阵列

60×75 mm、四层、正面贴装、99件实装。U2只是由用户在DFM中临时排除；本工程、BOM及贴装坐标仍保留ML307R-DL实装，U2铜面与V0.14.2相同。

RN3/RN4：共用封装的四个内脚焊盘宽度各增加0.04 mm，每边增加0.02 mm余量。板上影响8个焊盘，钢网开口保持。

J5：信号焊盘及钢网按厂家推荐位置向座子外侧移动0.224887 mm；一条接地线绕至座子外侧，新增顶层禁铜区。实际导出检查：禁布区顶层铜面积为0，两侧接地脚均能到达接地过孔，厂家允许布置焊盘区域内的信号触点有铜面与阻焊开口支撑。

已保存重开并核对实际制造文件；原生DRC=0。安装孔禁铜、U1和卡座前次修改保留。

尚未宣称工厂DFM全过。J5模型把座子内部部分触点也计入接触面积，其全模型接触比例仍可能报警；不能为消除该提示向厂家禁布区扩铜。此项应结合所附图纸进行工程复核。请重新加载本包工程/Gerber、BOM及CPL复查。
''',encoding='utf8')
doc.write_text(f'''# V0.14.4 天线座与电阻阵列复核记录

备份：`{stage['backupDirectory']}`。基线V0.14.2。本次不采用U2加宽草案，U2实装要求不变。

RN3、RN4共用0c60e13ae6df220b封装，仅2/3/6/7脚的焊盘宽度从约0.50增加至0.54 mm，长度约0.80 mm保持。增加0.02 mm/侧工程余量，标称模型至铜面最小约0.01999 mm。钢网使用旧版实际导出形状；器件位置、管脚号及电阻值保持。此为工程余量调整，不是宣称厂家发布了新的推荐焊盘。

J5所用U.FL-R-SMT(10)属Hirose旧U.FL系列。所附原厂目录第3页给出1.00×1.05 mm信号焊盘、信号焊盘内边缘距连接器中心1.00 mm，以及内部无导体布线区域。本工程J5库原点相对连接器中心在Y方向偏移0.65 mm，所以正确的信号焊盘中心局部Y为0.875 mm，边界Y=0.35～1.40 mm。原库中心Y约0.650113 mm，本次移动0.224887 mm。铜面/开窗/钢网同步移动，面积不增加。

原GND连线53c42a1c6259f3d6穿过该区域，本次改为在连接器上侧绕行，宽度0.254 mm保持；添加J5_HIROSE_NO_TOP_COPPER顶层禁铜区，防止后续铺铜重新侵入。实际新Gerber中此区铜面积为0，两侧地焊盘均有接地过孔连通。厂家允许焊盘区内的信号触点模型铜面外面积及开窗外面积均为0。检查为标称几何与参考图纸核对，不是回流焊实测或厂商工艺认可。

DFM的J5全模型接触比例尚不能作为已归零项目。原厂目录明确说明部分中心触点可能被绝缘材料覆盖；完整金属投影包括内部触点，不能要求把整段金属都焊在PCB上。全模型比例仍可能报警。保留该模型差异说明，不能用向禁布区扩铜的方法消除提示。

共修改5个主PAD、增加5个显式钢网FILL，板上影响9焊盘；修改1条GND线，增加1个顶层禁铜区，重建3块铺铜。原理图、104个封装实例、99件实装BOM/CPL、U2全部109焊盘及模型、310过孔、326钻孔、安装孔及两内层8个对应禁铜区保持。9份制造层/钻孔几何不变；钢网仅J5一个开口位置改变，面积及其他开口保持。

保存重开后核对通过，浮点序列化最大差值{maximum:.3g} mil；原生DRC=0。包括RN3/RN4在内的186个标称引脚模型核对通过。工厂完整DFM仍待重跑，不能以本地检查代替。

参考：[Hirose原厂U.FL目录（DigiKey托管）](https://media.digikey.com/pdf/data%20sheets/hirose%20pdfs/ufl%20series.pdf)，[Bourns原厂CAT/CAY16资料](https://www.bourns.com/data/global/pdfs/CATCAY.pdf)。
''',encoding='utf8')
# Render actual copper before/after. Red rectangle is the manufacturer's no-trace area.
exec((R/'scripts/render-hy20-gerber-v13.py').read_text(encoding='utf8').split('for label,copper,mask,silk in')[0])
def plane(path):
 global z
 z.close();z=zipfile.ZipFile(path);cache.clear();return unary_union([g for g,d in geom('Gerber_TopLayer.GTL')[0] if d])
oldcu=plane(old['productionGerber']);newcu=plane(E/'DTU-V0.14.4-60x75-Threefix-Gerber.zip')
im=Image.new('RGB',(1280,970),'#f5f7f6');dr=ImageDraw.Draw(im);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',21);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
for row,(ref,win) in enumerate([('RN3',(51.75,37.2,54.25,40.8)),('J5',(11.8,64.9,17.7,69.1))]):
 for col,(label,cu) in enumerate([('V0.14.2',oldcu),('V0.14.4',newcu)]):
  x0=25+640*col;y0=55+row*455;xb,yb,xe,ye=win;scale=min(580/(xe-xb),365/(ye-yb));xy=lambda x,y:(x0+(x-xb)*scale,y0+(ye-y)*scale)
  dr.rectangle([x0,y0,x0+580,y0+365],fill='#162b28');draw_geom(dr,cu.intersection(box(*win)),'#d6ba6e',xy);dr.text((x0,y0-30),f'{ref} / {label}',font=font,fill='#18382e')
  if ref=='J5':
   coords=[xy(x,y) for x,y in [(13.05,66.35),(14.95,66.35),(14.95,68.45),(13.05,68.45),(13.05,66.35)]];dr.line(coords,fill='#ff7272',width=2);dr.text((x0+5,y0+340),'Red: no top copper under connector',font=small,fill='#ffffff')
dr.text((25,932),'Actual exported copper. J5 full-model DFM overlap remains a documented model exception.',font=small,fill='#18382e')
preview=E/'DTU-V0.14.4-Threefix-before-after.png';im.save(preview)
files=[E/'DTU-V0.14.4-60x75-Threefix.epro2',E/'DTU-V0.14.4-60x75-Threefix-Gerber.zip',E/'DTU-V0.14.4-Threefix-BOM-99.csv',E/'DTU-V0.14.4-Threefix-CPL-99-Top.csv',readme,doc,preview]
bundle=E/'DTU-V0.14.4-60x75-天线座与电阻阵列复查包.zip'
manifest=copy.deepcopy(old);manifest.update({'revision':'V0.14.4 天线座与电阻阵列复核 2026-10-16','backupDirectory':stage['backupDirectory'],'projectUuid':'ba912ce2dfad253c22e034fef383544af50374bc5b74a7f6f0299caf191a7a67','nativeProject':str(files[0].resolve()),'productionGerber':str(files[1].resolve()),'deliveryArchive':str(bundle.resolve()),'actualCopperManifest':'threefix-actual-routing-v14_4.json','actualSourceSnapshot':'threefix-reopened-source-v14_4.json','pinLandVerification':'threefix-verification-v14_4.json','J5ManufacturerReview':'threefix-J5-manufacturer-review-v14_4.json','factoryDfmPassed':False,'U2AssemblyStillRequired':True,'files':[{'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]})
save(M/'current-pcb-delivery-v14_4.json',manifest)
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as zz:
 for p in files:zz.write(p,p.name)
 for p,name in [(M/'threefix-verification-v14_4.json','制造文件核对.json'),(M/'threefix-J5-manufacturer-review-v14_4.json','J5模型差异及焊接区核对.json'),(M/'current-pcb-delivery-v14_4.json','版本清单.json'),(R/'references/Hirose-UFL-legacy.pdf','Hirose-UFL原厂参考.pdf')]:zz.write(p,name)
with zipfile.ZipFile(bundle) as zz:
 assert zz.testzip() is None
 for p in files:assert zz.read(p.name)==p.read_bytes()
for n in ['current-pcb-delivery.json','current-pcb-delivery-v13.json','current-pcb-delivery-v14.json']:save(M/n,manifest)
for p,n in [(files[0],'DTU-current.epro2'),(files[1],'DTU-current-Gerber.zip'),(files[2],'DTU-current-BOM.csv'),(files[3],'DTU-current-CPL-Top.csv'),(bundle,'DTU-current-review.zip')]:shutil.copy2(p,E/n)
(E/'当前版本说明.md').write_text('当前版本：V0.14.4，60×75 mm，四层、正面贴装。\n\n请使用 DTU-V0.14.4-60x75-天线座与电阻阵列复查包.zip。U2保留实装，未采用U2加宽草案。RN3/RN4边界余量修正，J5按原厂焊接/禁布区修正；J5全模型DFM比例仍可能提示，详见包内说明。\n',encoding='utf8')
print('Packaged',bundle,'bytes',bundle.stat().st_size)
