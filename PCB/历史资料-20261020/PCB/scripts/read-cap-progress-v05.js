return {doc:await eda.dmt_SelectControl.getCurrentDocumentInfo(),c110:(await eda.sch_PrimitiveComponent.getAll("part")).filter(c=>c.getState_Designator()==="C110").map(c=>c.getState_PrimitiveId())};
