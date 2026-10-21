if((await eda.dmt_Project.getCurrentProjectInfo())?.uuid!=='be907e0c26ece4ccdedd2f5b24e25f76812bc6b957961675838d5450e3220cbc')throw Error('Wrong project');
await eda.dmt_EditorControl.openDocument('8902a3019bd8d84c');
const f=await eda.sch_ManufactureData.getNetlistFile('DTU-V0.12-schematic-netlist','EasyEDA');if(!f)throw Error('No netlist');
const result={name:f.name,bytes:Array.from(new Uint8Array(await f.arrayBuffer()))};
await eda.dmt_EditorControl.openDocument('4211128ecf040c100b33238447713203');return result;
