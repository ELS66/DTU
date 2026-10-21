const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();return {activated:await eda.dmt_EditorControl.activateDocument(d.tabId)};
