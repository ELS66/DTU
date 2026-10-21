from pathlib import Path
import json,zipfile,shutil,csv,hashlib,datetime
P=Path('PCB');E=P/'eda';M=P/'manifests'
drc=json.loads((M/'check-pcb-routing-opt-v13.json').read_text())['result'];assert drc==[]
source=json.loads((M/'routing-opt-source-verification-v13.json').read_text());assert source['protectedCopperUnchanged'] and source['nativeCopperMatchesCandidate']
assert json.loads((M/'routing-opt-connectivity-v13.json').read_text())['regressions']==[]
copper=json.loads((M/'routing-opt-actual-copper-check-v13.json').read_text());assert copper['conflicts']==[]
manufacturing=json.loads((M/'routing-opt-manufacturing-check-v13.json').read_text());assert manufacturing['totalDrilledHoles']==326
with (P/'reports/V0.13-布线优化网络对比.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['网络','优化前过孔数','优化后过孔数'])
 for r in json.loads((M/'routing-opt-connectivity-v13.json').read_text())['netChanges']:w.writerow([r['net'],r['before'],r['after']])
files=[E/'DTU-V0.13-60x70-routing-optimized.epro2',E/'DTU-V0.13-60x70-routing-optimized-Gerber.zip',E/'DTU-V0.13-BOM-99.csv',E/'DTU-V0.13-CPL-99-Top.csv',E/'DTU-V0.13-BOM-review.csv',E/'DTU-V0.13-optimized-Gerber-top.png',E/'DTU-V0.13-optimized-Gerber-bottom.png',E/'DTU-V0.13-placement-1.png',P/'docs/V0.13-整体验收记录.md',P/'docs/V0.13-布线优化记录.md',E/'DTU-V0.13-README.md',P/'reports/V0.13-布线优化网络对比.csv']
target=E/'DTU-V0.13-60x70-布线优化资料包.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
 for f in files:
  assert f.is_file() and f.stat().st_size>0
  z.write(f,f.name)
with zipfile.ZipFile(target) as z:assert z.testzip() is None and len(z.namelist())==12
with zipfile.ZipFile(E/'DTU-V0.13-60x70-routing-optimized-Gerber.zip') as z:assert z.testzip() is None and len(z.namelist())==12
# Update earlier delivery links; their original bytes remain in the pre-optimization backup.
for src,dest in [('DTU-V0.13-60x70-routing-optimized.epro2','DTU-V0.13-60x70-DFM-review.epro2'),('DTU-V0.13-60x70-routing-optimized-Gerber.zip','DTU-V0.13-60x70-SMT-4L-Gerber-DFM.zip'),('DTU-V0.13-60x70-routing-optimized-raw','DTU-V0.13-60x70-DFM-review'),('DTU-V0.13-60x70-布线优化资料包.zip','DTU-V0.13-60x70-验收资料包.zip')]:shutil.copy2(E/src,E/dest)
for layer in ['top','bottom','inner1','inner2']:shutil.copy2(E/f'DTU-V0.13-optimized-Gerber-{layer}.png',E/f'DTU-V0.13-Gerber-{layer}.png')
shutil.copy2(M/'routing-optimized-source-v13.json',M/'final-connected-routing-v13.json')
shutil.copy2(M/'routing-opt-actual-copper-check-v13.json',M/'final-copper-check-v13.json')
shutil.copy2(M/'check-pcb-routing-opt-v13.json',M/'check-pcb-v13.json')
(M/'final-gerber-dfm-check-v13.json').write_text(json.dumps({'silkToMaskMinimumMm':manufacturing['topSilkMaskClearanceMm'],'holeToHoleMinimumMm':manufacturing['minimumDrillWallGapMm'],'allFourCopperLayersPresent':True,'topSmtConnectors':3,'factoryDfmPassed':False},indent=2))
# Keep the traditional full drill-detail manifest current.
exec((P/'scripts/render-routing-opt-gerber-v13.py').read_text(encoding='utf-8-sig').split('for label,copper,mask,silk in')[0])
drillreport={n:{'count':len(drill(n)),'sizes':dict(__import__('collections').Counter(round(q[2],3) for q in drill(n))),'points':drill(n)} for n in ['Drill_PTH_Through.DRL','Drill_NPTH_Through.DRL']}
(M/'final-drill-check-v13.json').write_text(json.dumps(drillreport,indent=2))
backup=P/'backups/20261015-before-routing-optimization'
backupfiles=[{'file':str(f.relative_to(backup)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size} for f in backup.rglob('*') if f.is_file() and f.name!='backup-manifest.json']
(backup/'backup-manifest.json').write_text(json.dumps({'created':datetime.datetime.now().isoformat(),'files':backupfiles},indent=2),encoding='utf8')
current={'revision':'V0.13 routing optimized 2026-10-15','boardMm':[60,70],'layers':4,'assembly':'Top','components':104,'defaultAssembly':99,'vias':310,'drilledHoles':326,'pcbDrcIssues':0,'schematicWarnings':18,'backupDirectory':str(backup.resolve()),'nativeProject':str((E/'DTU-V0.13-60x70-routing-optimized.epro2').resolve()),'productionGerber':str((E/'DTU-V0.13-60x70-routing-optimized-Gerber.zip').resolve()),'deliveryArchive':str(target.resolve()),'actualCopperManifest':'routing-optimized-source-v13.json','actualSourceSnapshot':'source-after-routing-opt-v13.json','factoryDfmPassed':False}
(M/'current-pcb-delivery-v13.json').write_text(json.dumps(current,indent=2),encoding='utf8')
print(json.dumps({'package':str(target),'bytes':target.stat().st_size,'packageFiles':len(files),'backupFiles':len(backupfiles),'vias':310,'pcbDrcIssues':0},ensure_ascii=True))
