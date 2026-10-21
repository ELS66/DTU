if((await eda.dmt_Project.getCurrentProjectInfo())?.uuid!=='be907e0c26ece4ccdedd2f5b24e25f76812bc6b957961675838d5450e3220cbc')throw Error('Wrong source project');
const f=globalThis.dtuV12FinalFile;if(!f||f.name!=='DTU-V0.12-ML307R-DL-60x70.epro2')throw Error('Final file not inspected');
globalThis.dtuV12ImportState={state:'running'};
try{const result=await eda.sys_FileManager.importProjectByProjectFile(f,'EasyEDA Pro',undefined,{operation:'Offline Client Local Path',folderPath:'D:/DTU/PCB/eda/DTU-V0.12-ML307R-DL-60x70'});if(!result)throw Error('No imported project');globalThis.dtuV12ImportState={state:'finished',result};return result;}catch(e){globalThis.dtuV12ImportState={state:'failed',error:String(e)};throw e;}
