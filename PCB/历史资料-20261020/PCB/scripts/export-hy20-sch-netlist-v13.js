if((await eda.dmt_Project.getCurrentProjectInfo())?.uuid!=='52c709566e222603927d1a7d15a5e220a7f38cb78f29ecab14bf35ab4cfcb0b9')throw Error('Wrong project');
await eda.dmt_EditorControl.openDocument('8902a3019bd8d84c');
const f=await eda.sch_ManufactureData.getNetlistFile('DTU-V0.13-HY20-schematic-netlist','EasyEDA');if(!f)throw Error('No netlist');
const result={name:f.name,bytes:Array.from(new Uint8Array(await f.arrayBuffer()))};
await eda.dmt_EditorControl.openDocument('4211128ecf040c100b33238447713203');return result;
