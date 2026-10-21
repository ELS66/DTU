const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();if(d?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");return await eda.dmt_EditorControl.zoomToAllPrimitives(d.tabId);
