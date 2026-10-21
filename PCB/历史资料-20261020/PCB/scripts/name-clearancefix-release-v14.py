from pathlib import Path
import json,zipfile,base64,copy
R=Path('PCB');E=R/'eda';M=R/'manifests'
s=(R/'scripts/package-silkclean-v13.py').read_text(encoding='utf8');exec(s[s.index('def active_project('):s.index('oldproj=active_project(')])
s=(R/'scripts/prepare-clearancefix-v14.py').read_text(encoding='utf8');exec(s[s.index('def write_project('):s.index("if __name__=='__main__':")])
source=E/'DTU-V0.14-60x75-Clearancefix.epro2';a=active_project(source);k=('BOARD','e7a0217c7788eb0d','META','META');q=copy.deepcopy(a[k]);q['title']='DTU_V0.14_正面贴片_60x75'
temp=E/'DTU-V0.14-Clearancefix-name-stage.epro2';write_project(source,temp,{k:q})
target=E/'DTU-V0.14-60x75-Clearancefix-release-input.epro2'
with zipfile.ZipFile(temp) as z,zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as dest:
 for n in z.namelist():
  content=z.read(n)
  if n=='project2.json':
   p=json.loads(content);p['title']='DTU-V0.14-ML307R-DL-单面贴装-60x75';content=json.dumps(p,ensure_ascii=False,indent=2).encode('utf8')
  dest.writestr(n,content)
folder=str((R/'native-Clearancefix-release-v14').resolve());Path(folder).mkdir(exist_ok=True)
u=json.loads((M/'clearancefix-project-id-v14.json').read_text(encoding='utf8'))['uuid']
js='if((await eda.dmt_Project.getCurrentProjectInfo())?.uuid!=='+json.dumps(u)+")throw Error('Wrong verified PCB');const f=new File([Uint8Array.from(atob("+json.dumps(base64.b64encode(target.read_bytes()).decode())+"),c=>c.charCodeAt(0))],'DTU-V0.14-60x75-Clearancefix.epro2');return {imported:await eda.sys_FileManager.importProjectByProjectFile(f,'JLCEDA Pro',{importOption:'ImportDocument',associateFootprint:true,associate3DModel:true,importFootprintNotesLayer:true},{operation:'Offline Client Local Path',folderPath:"+json.dumps(folder)+"})};"
(R/'scripts/import-clearancefix-release-v14.js').write_text(js,encoding='utf8')
