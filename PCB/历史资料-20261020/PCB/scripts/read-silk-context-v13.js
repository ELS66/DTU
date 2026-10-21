return {project:await eda.dmt_Project.getCurrentProjectInfo(),document:await eda.dmt_SelectControl.getCurrentDocumentInfo(),pcbs:await eda.dmt_Pcb.getAllPcbsInfo()};
