if((await eda.dmt_Project.getCurrentProjectInfo())?.uuid!=='be907e0c26ece4ccdedd2f5b24e25f76812bc6b957961675838d5450e3220cbc')throw Error('Wrong project');
const all=await eda.dmt_Schematic.getAllSchematicPagesInfo();const out=[];
for(const p of all){await eda.dmt_EditorControl.openDocument(p.uuid);const updated=await eda.dmt_Schematic.modifySchematicPageTitleBlock(undefined,{'Version':{showTitle:false,showValue:false,value:'V0.12'},'Name':{showTitle:false,showValue:false,value:'ESP32-C5 + ML307R-DL'},'Description':{showTitle:false,showValue:false,value:'60 x 70 mm'}});if(!updated)throw Error('Title update failed');out.push({uuid:p.uuid,updated,saved:await eda.sch_Document.save()});}
await eda.dmt_EditorControl.openDocument('4211128ecf040c100b33238447713203');return out;
