const cs=await eda.sch_PrimitiveComponent.getAll("part");return cs.map(c=>({ref:c.getState_Designator(),id:c.getState_PrimitiveId(),sub:c.getState_SubPartName(),x:c.getState_X(),y:c.getState_Y()}));
