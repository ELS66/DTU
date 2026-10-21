from pathlib import Path
import os,json,hashlib,csv

root=Path('D:/DTU'); pcb=root/'PCB'
final=pcb/'V0.14.4-最终资料'; history=pcb/'历史资料-20261020'
assert not final.exists() and not history.exists(), 'Target folders already exist'
history.mkdir(); final.mkdir()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
old=json.loads((pcb/'manifests/current-pcb-delivery.json').read_text(encoding='utf-8-sig'))
for f in old['files'][:4]:
 p=pcb/'eda'/f['file'];assert sha(p)==f['sha256'],str(p)
copies=[]
def add(src,dest):
 src=Path(src);dest=final/dest
 assert src.is_file(),str(src)
 copies.append(dict(source=str(src),destination=str(dest),sha256=sha(src),bytes=src.stat().st_size))
add(pcb/'eda/DTU-V0.14.4-60x75-Threefix.epro2',Path('01-工程/DTU-V0.14.4-60x75-Threefix.epro2'))
add(pcb/'native-Threefix-final-v14_4/DTU-V0.14.4-三处修正-60x75.eprj2',Path('01-工程/DTU-V0.14.4-三处修正-60x75.eprj2'))
for name in ['DTU-V0.14.4-60x75-Threefix-Gerber.zip','DTU-V0.14.4-Threefix-BOM-99.csv','DTU-V0.14.4-Threefix-CPL-99-Top.csv']:
 add(pcb/'eda'/name,Path('02-制造基准')/name)
add(root/'outputs/bom-20261020-purchase/DTU-V0.14.4-BOM-本次采购验证版-20261020.xlsx',Path('03-本次采购/DTU-V0.14.4-BOM-本次采购验证版-20261020.xlsx'))
add(Path('D:/download/订单数据 (1).xlsx'),Path('03-本次采购/订单数据-20261020.xlsx'))
add(root/'outputs/bom-review-20261020/更新订单采购核对-20261020.md',Path('03-本次采购/采购核对记录-更新BOM前.md'))
for name in ['V0.14-封装边界与模组净空修正记录.md','V0.14.1-安装孔禁铜错位修正记录.md','V0.14.2-引脚边界修正记录.md','V0.14.4-天线座与电阻阵列复核记录.md']:
 add(pcb/'docs'/name,Path('04-验证资料')/name)
add(pcb/'eda/DTU-V0.14.4-Threefix-README.md',Path('04-验证资料/原工程导出说明-20261016.md'))
add(pcb/'eda/DTU-V0.14.4-Threefix-before-after.png',Path('04-验证资料/天线座与排阻修正对比.png'))
evidence=['threefix-actual-routing-v14_4.json','threefix-reopened-source-v14_4.json','threefix-drc-v14_4.json','threefix-verification-v14_4.json','threefix-J5-manufacturer-review-v14_4.json','mountfix-verification-v14_1.json','pinfix-verification-v14_2.json']
for name in evidence:add(pcb/'manifests'/name,Path('04-验证资料')/name)
moves=[]
def move(src,dst):
 src=Path(src);dst=Path(dst)
 assert src.exists() and not dst.exists()
 assert src.resolve().is_relative_to(root.resolve()) and dst.resolve().is_relative_to(root.resolve())
 moves.append(dict(source=str(src),destination=str(dst)))
for name in ['eda','backups','reports','docs','manifests','scripts']:
 move(pcb/name,history/'PCB'/name)
for p in sorted(pcb.glob('native-*')):move(p,history/'PCB'/p.name)
for name in ['README.md','DTU主板硬件设计与API绘板规范.md']:
 move(pcb/name,history/'PCB'/name)
for p in sorted((root/'outputs').iterdir()):move(p,history/'outputs'/p.name)
inventory=[];links=[]
def islink(p):return p.is_symlink() or (hasattr(p,'is_junction') and p.is_junction())
for m in moves:
 src=Path(m['source']); dst=Path(m['destination'])
 if src.is_file():files=[src]
 else:
  files=[]
  for current,dirs,names in os.walk(src,followlinks=False):
   for name in list(dirs):
    p=Path(current)/name
    if islink(p):
     dirs.remove(name);links.append(dict(source=str(p),destination=str(dst/p.relative_to(src)),target=str(p.resolve())))
   files.extend(Path(current)/name for name in names)
 for p in files:
  target=dst if src.is_file() else dst/p.relative_to(src)
  inventory.append(dict(source=str(p),destination=str(target),bytes=p.stat().st_size,sha256=sha(p)))
plan=dict(workspace=str(root),finalDirectory=str(final),historyDirectory=str(history),copyFiles=copies,moves=moves,files=inventory,junctions=links,oldDeliveryManifest=old)
(history/'归档迁移计划.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
with (history/'文件迁移清单.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['source','destination','bytes','sha256']);w.writeheader();w.writerows(inventory)
print(json.dumps({'final':str(final),'history':str(history),'copyFiles':len(copies),'moveItems':len(moves),'historyFiles':len(inventory),'historyMB':round(sum(r['bytes'] for r in inventory)/1e6,1),'junctionsPreservedWithoutFollowing':len(links)},ensure_ascii=False))
