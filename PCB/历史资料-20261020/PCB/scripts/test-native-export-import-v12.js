if((await eda.dmt_Project.getCurrentProjectInfo())?.uuid!=='be907e0c26ece4ccdedd2f5b24e25f76812bc6b957961675838d5450e3220cbc')throw Error('Wrong source project');
const f=await eda.sys_FileManager.getProjectFile('DTU-V0.12-ML307R-DL-60x70',undefined,'epro2');if(!f)throw Error('No native export');
globalThis.dtuV12NativeImport={state:'running',name:f.name,type:f.type};
const result=await eda.sys_FileManager.importProjectByProjectFile(f,'EasyEDA Pro',undefined,{operation:'Offline Client Local Path',folderPath:'D:/DTU/PCB/eda/DTU-V0.12-ML307R-DL-60x70'});
globalThis.dtuV12NativeImport={state:'finished',result,name:f.name,type:f.type};return globalThis.dtuV12NativeImport;
