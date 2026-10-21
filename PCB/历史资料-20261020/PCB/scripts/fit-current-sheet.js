const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();return {bounds:await eda.dmt_EditorControl.zoomToAllPrimitives(d.tabId)};
