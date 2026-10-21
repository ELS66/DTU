if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=='4211128ecf040c100b33238447713203')throw Error('Wrong PCB');return (await eda.pcb_PrimitiveFill.getAll(16,'GND')).map(p=>({id:p.getState_PrimitiveId(),polygon:p.getState_ComplexPolygon().getSource()}));

