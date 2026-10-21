if((await eda.dmt_Project.getCurrentProjectInfo())?.uuid!=='be907e0c26ece4ccdedd2f5b24e25f76812bc6b957961675838d5450e3220cbc')throw Error('Wrong source project');
const raw=globalThis.dtuV12FinalFile;if(!raw)throw Error('File not inspected');
const f=new File([raw],raw.name,{type:'zip'});
const result=await eda.sys_FileManager.importProjectByProjectFile(f,'EasyEDA Pro',undefined,{operation:'Offline Client Local Path',folderPath:'D:/DTU/PCB/eda/V0.12-final-60x70'});
globalThis.dtuV12BrandedCleanProject=result;return {result};
