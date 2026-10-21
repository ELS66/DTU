if((await eda.dmt_Project.getCurrentProjectInfo())?.uuid!=='be907e0c26ece4ccdedd2f5b24e25f76812bc6b957961675838d5450e3220cbc'||(await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=='4211128ecf040c100b33238447713203')throw Error('Wrong PCB');
if(globalThis.dtuV12Repair?.state==='running')throw Error('Native routing still active');
const all=await eda.pcb_PrimitiveVia.getAll();const small=all.find(v=>v.getState_PrimitiveId()==='03c614ee7b1d16b1');const large=all.find(v=>v.getState_PrimitiveId()==='3939d821ce44229e');
if(!small||!large||small.getState_Net()!=='VDD_4G'||large.getState_Net()!=='VDD_4G')throw Error('Via state changed');
return {deleted:await eda.pcb_PrimitiveVia.delete(['03c614ee7b1d16b1']),saved:await eda.pcb_Document.save()};
