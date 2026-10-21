const uuid='fd71bf4d415315427fd7a027a4dd7e0a77d66de0d184ebd89693182b3f596907';
if(!await eda.dmt_Project.openProject(uuid))throw Error('Project open failed');
await eda.dmt_EditorControl.openDocument('4211128ecf040c100b33238447713203');
const p=await eda.dmt_Project.getCurrentProjectInfo();const d=await eda.dmt_SelectControl.getCurrentDocumentInfo();
return {project:p?.uuid,name:p?.friendlyName,document:d?.uuid,board:await eda.dmt_Board.getCurrentBoardInfo()};
