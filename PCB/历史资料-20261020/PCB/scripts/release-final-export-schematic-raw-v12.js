if((await eda.dmt_Project.getCurrentProjectInfo())?.uuid!=='da9775b4e341e163260ddd9bb097311369dc525f008e7fcc093462a87b61a989')throw Error('Wrong project');
await eda.dmt_EditorControl.openDocument('8902a3019bd8d84c');
const f=await eda.sch_ManufactureData.getNetlistFile('DTU-V0.12-schematic-netlist','EasyEDA');if(!f)throw Error('No netlist');
const result={name:f.name,bytes:Array.from(new Uint8Array(await f.arrayBuffer()))};
await eda.dmt_EditorControl.openDocument('4211128ecf040c100b33238447713203');return result;
