import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {Workbook, SpreadsheetFile, FileBlob} from '@oai/artifact-tool';

const dir = 'D:/DTU/outputs/bom-20261019';
const costMode=process.argv.includes('--cost');
const costDir='D:/DTU/outputs/bom-cost-20261019';
const source = 'D:/DTU/PCB/eda/DTU-V0.14.4-Threefix-BOM-99.csv';
const raw = await Workbook.fromCSV((await fs.readFile(source, 'utf8')).replace(/^\uFEFF/, ''), {sheetName:'Source'});
const rows = raw.worksheets.getItemAt(0).getUsedRange().values;
assert.deepEqual(rows[0], ['Designator','Comment','Footprint','LCSC Part #']);
const parts = rows.slice(1).filter(r=>r[0]);
assert.equal(parts.length,99);
assert.equal(new Set(parts.map(r=>r[0])).size,99);
const groups = new Map();
for (const [ref,comment,footprint,code] of parts) {
  assert.ok(code && footprint);
  const key = code+'\t'+footprint;
  if (!groups.has(key)) groups.set(key,{code,footprint,refs:[],comments:new Set()});
  const group=groups.get(key);
  group.refs.push(ref); group.comments.add(comment);
}
const natural = new Intl.Collator('en',{numeric:true});
const grouped=[...groups.values()];
for(const g of grouped) g.refs.sort(natural.compare);
grouped.sort((a,b)=>natural.compare(a.refs[0],b.refs[0]));
const models=JSON.parse(await fs.readFile(`${dir}/manufacturer-models.json`,'utf8'));
if(costMode){
  const review=JSON.parse(await fs.readFile(`${costDir}/U6-replacement-review.json`,'utf8'));
  assert.equal(review.pcbGeometryChanged,false);
  assert.equal(review.pads.length,8);
  const u6=grouped.find(g=>g.refs.includes('U6'));
  assert.deepEqual(u6.refs,['U6']);
  assert.equal(u6.code,'C1545222');
  u6.code='C8963';
  u6.comments=new Set(['SP3485EN-L/TR']);
  models.C8963={model:'SP3485EN-L/TR',package:'SOIC-8'};
}
const typeFor=g=>{
  const ref=g.refs[0];
  if(ref.startsWith('RN'))return '贴片排阻';
  if(ref.startsWith('R'))return '贴片电阻';
  if(ref.startsWith('C'))return g.code==='C128504'?'固态铝聚合物电容':'贴片陶瓷电容';
  if(ref.startsWith('D'))return Number(ref.slice(1))>=30?'发光二极管':'二极管';
  if(ref.startsWith('F'))return '自恢复保险丝';
  if(ref.startsWith('L'))return '功率电感';
  if(ref.startsWith('Q'))return '晶体管';
  if(ref==='J4')return 'SIM 卡座';
  if(ref==='J5')return '射频连接器';
  if(ref.startsWith('J'))return '线对板连接器';
  if(ref==='U1')return 'Wi-Fi / 蓝牙模块';
  if(ref==='U2')return '4G 通信模块';
  if(ref==='U6')return 'RS485 收发器';
  return '集成电路';
};
const data=grouped.map(g=>{
  assert.ok(models[g.code]?.model && models[g.code]?.package,`Missing manufacturer model: ${g.code}`);
  return [typeFor(g),models[g.code].model,models[g.code].package,g.refs.length];
});
assert.equal(data.reduce((s,r)=>s+r[3],0),99);
assert.deepEqual(grouped.flatMap(g=>g.refs).sort(natural.compare),parts.map(r=>r[0]).sort(natural.compare));
assert.equal(grouped.find(g=>g.refs.includes('U2')).code,'C48982537');
for(const ref of ['C50','C51','R32','J6','J7']) assert.ok(!grouped.some(g=>g.refs.includes(ref)));

const wb=Workbook.create();
const sheet=wb.worksheets.add('物料清单');
sheet.showGridLines=false;
const end=data.length+5;
const total=end+1;
sheet.getRange(`A1:D${total}`).format.font={name:'Arial',size:11,color:'#1F2937'};
sheet.getRange(`A1:D${total}`).format.verticalAlignment='center';
sheet.getRange('A2').values=[['DTU V0.14.4 物料清单']];
sheet.getRange('A2').format.font={name:'Arial',size:15,bold:true};
sheet.getRange('A3').values=[[`${data.length} 种物料，数量为单块板用量，包含 U2。`]];
sheet.getRange('A3').format.font={name:'Arial',size:10,color:'#5B6472'};
if(costMode){
  sheet.getRange('A2').values=[['DTU V0.14.4 免改板降本候选']];
  sheet.getRange('A3').values=[['单板用量。U6 拟换 SP3485EN-L/TR，首板验证后定版。']];
}
sheet.getRange('A5:D5').values=[['物料类型','完整型号','封装','数量']];
sheet.getRange(`A6:D${end}`).values=data;
const table=sheet.tables.add(`A5:D${end}`,true,'BomQuantity');
table.showFilterButton=true;
sheet.getRange('A5:D5').format={fill:'#243C5A',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',verticalAlignment:'center',rowHeight:30};
sheet.getRange('A5:D5').format.borders={insideVertical:{style:'thin',color:'#FFFFFF'}};
sheet.getRange(`A6:D${end}`).format.wrapText=true;
sheet.getRange(`A6:D${end}`).format.rowHeight=30;
sheet.getRange(`B6:C${end}`).setNumberFormat('@');
data.forEach((r,i)=>{if(/^\d{4}$/.test(r[2])) sheet.getRange(`C${i+6}`).setNumberFormat('0000');});
sheet.getRange(`D6:D${total}`).setNumberFormat('#,##0');
sheet.getRange(`D6:D${total}`).format.horizontalAlignment='right';
for(const [column,width] of [['A',220],['B',390],['C',270],['D',95]]) sheet.getRange(`${column}1:${column}${total}`).format.columnWidthPx=width;
sheet.getRange('A2:D2').format.rowHeight=30;
sheet.getRange('A3:D3').format.rowHeight=26;
sheet.getRange(`A${total}`).values=[['单板贴装总数量']];
sheet.getRange(`D${total}`).formulas=[[`=SUM(D6:D${end})`]];
sheet.getRange(`A${total}:D${total}`).format={fill:'#E8EDF4',font:{name:'Arial',size:11,bold:true},rowHeight:30};
sheet.freezePanes.freezeRows(5);
let costSheet;
if(costMode){
  const quote=await SpreadsheetFile.importXlsx(await FileBlob.load('D:/download/DTU-V0.14.4-BOM-按型号汇总-含数量 (1).xlsx'));
  const quotedRows=quote.worksheets.getItemAt(0).getUsedRange().values.slice(1).filter(r=>r[3]);
  assert.equal(quotedRows.length,48);
  assert.ok(quotedRows.every(r=>r[5]===r[4]*5));
  const oldTotal=quotedRows.reduce((s,r)=>s+r[6],0);
  const oldU6=quotedRows.find(r=>r[1]==='U6')[6];
  assert.equal(oldTotal,531.5); assert.equal(oldU6,60);
  costSheet=wb.worksheets.add('费用测算');
  const c=costSheet;
  c.showGridLines=false;
  c.getRange('A1:C27').format.font={name:'Arial',size:11,color:'#1F2937'};
  c.getRange('A1:C27').format.verticalAlignment='center';
  for(const [col,width] of [['A',235],['B',150],['C',660]])c.getRange(`${col}1:${col}27`).format.columnWidthPx=width;
  c.getRange('A2').values=[['五块打样费用测算']];
  c.getRange('A2').format.font={name:'Arial',size:15,bold:true};
  c.getRange('A3').values=[['黄色单元格可填写。新料人民币单价尚未取得报价。']];
  c.getRange('A3').format.font={name:'Arial',size:10,color:'#5B6472'};
  c.getRange('A5:C5').values=[['项目','数值','说明']];
  c.getRange('A5:C5').format={fill:'#243C5A',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',rowHeight:30};
  c.getRange('A6:C15').values=[
    ['板数量',5,'按本次五块板打样计算'],
    ['原器件金额（元）',oldTotal,'来源：用户提供的五块板器件报价。'],
    ['原 U6 金额（元）',oldU6,'5 颗 MAX3485ESA+，原报价每颗 12 元。'],
    ['其余物料金额（元）',null,'保留原报价中的其他 47 种物料。'],
    ['新 U6 单价（元）',null,'填写实际人民币成交单价，勿填美元网页价格。'],
    ['新 U6 采购数量',6,'5 颗贴装加 1 颗备用，可按起订量和贴片厂备损调整。'],
    ['替料后采购金额（元）',null,'其余物料原报价加新 U6 采购金额，不含新增贴片费用。'],
    ['较原报价节省（元）',null,'负值表示本次采购反而更贵。'],
    ['折合每板金额（元）',null,'按采购总支出分摊到五块板，含备用 U6。'],
    ['U6 保本单价（元）',null,'新 U6 单价低于此值，本次采购金额才低于原 U6 金额。']
  ];
  c.getRange('B9').formulas=[['=B7-B8']];
  c.getRange('B12').formulas=[['=IF(ISNUMBER(B10),SUM(B9,B10*B11),"待报价")']];
  c.getRange('B13').formulas=[['=IF(ISNUMBER(B12),B7-B12,"待报价")']];
  c.getRange('B14').formulas=[['=IF(ISNUMBER(B12),B12/B6,"待报价")']];
  c.getRange('B15').formulas=[['=B8/B11']];
  c.getRange('B6:B15').setNumberFormat('#,##0.00');
  for(const addr of ['B6','B11'])c.getRange(addr).setNumberFormat('0');
  c.getRange('B10:B11').format.fill='#FFF1C2';
  c.getRange('B6:B15').format.horizontalAlignment='right';
  c.getRange('A6:C15').format.rowHeight=30;
  c.getRange('A18:C22').values=[
    ['替换范围','U6','MAX3485ESA+ → SP3485EN-L/TR（MaxLinear，C8963）'],
    ['供电差异','3.3 V ±5%','新料按 3.135～3.465 V 表征，原料为 3.0～3.6 V。'],
    ['首板验证',null,'核对供电波动、所需波特率、收发切换、空闲状态及现场线缆。'],
    ['其余器件',null,'U1 仍为 N8R4，U2 仍为 ML307R-DL。保留全部接口、8 灯及保护。'],
    ['工程状态',null,'采购替代候选。原工程标注、Gerber 与贴装坐标未修改。']
  ];
  c.getRange('A18:C22').format.rowHeight=32;
  c.getRange('A24').values=[['报价来源']];
  c.getRange('C24').values=[['用户提供五块板 BOM 报价（2026-10-19）。']];
  c.getRange('A25').values=[['候选物料']];
  c.getRange('C25').values=[['https://item.szlcsc.com/9482.html']];
  c.getRange('A26').values=[['原厂手册']];
  c.getRange('C26').values=[['https://www.maxlinear.com/ds/sp3485.pdf']];
  c.getRange('A27').values=[['同芯片包装替代']];
  c.getRange('C27').values=[['MAX3485ESA+T（ADI/MAXIM，C18148），可另询价比较。']];
  c.getRange('A24:C27').format.rowHeight=28;
  // Verify blank versus zero and the quoted-input calculation before restoring the blank input.
  assert.equal(c.getRange('B12').values[0][0],'待报价');
  c.getRange('B10').values=[[2]];
  assert.equal(c.getRange('B12').values[0][0],483.5);
  assert.equal(c.getRange('B13').values[0][0],48);
  c.getRange('B10').values=[[0]];
  assert.equal(c.getRange('B12').values[0][0],471.5);
  c.getRange('B10').clear({applyTo:'contents'});
}
wb.recalculate();
assert.equal(sheet.getRange(`D${total}`).values[0][0],99);
console.log((await wb.inspect({kind:'table',range:'物料清单!A5:D10',include:'values,formulas',tableMaxRows:6,tableMaxCols:4,maxChars:2000})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!',options:{useRegex:true,maxResults:20},summary:'Formula error scan',maxChars:1000})).ndjson);
for(const [name,range] of [['four-columns','A1:D'+total]]) {
  const preview=await wb.render({sheetName:sheet.name,range,scale:1.25,format:'png'});
  await fs.writeFile(`${costMode?costDir:dir}/preview-${name}.png`,new Uint8Array(await preview.arrayBuffer()));
}
if(costMode){
  assert.equal(costSheet.getRange('B12').values[0][0],'待报价');
  assert.equal(costSheet.getRange('B9').values[0][0],471.5);
  console.log((await wb.inspect({kind:'table',range:'费用测算!A6:B15',include:'values,formulas',tableMaxRows:10,tableMaxCols:2,maxChars:1800})).ndjson);
  const preview=await wb.render({sheetName:costSheet.name,range:'A1:C27',scale:1.25,format:'png'});
  await fs.writeFile(`${costDir}/preview-cost.png`,new Uint8Array(await preview.arrayBuffer()));
  const q=x=>'"'+String(x).replaceAll('"','""')+'"';
  const upload=[['Comment','Designator','Footprint','LCSC Part #','Quantity'],...grouped.map(g=>[models[g.code].model,g.refs.join(', '),g.footprint,g.code,g.refs.length])];
  await fs.writeFile(`${costDir}/DTU-V0.14.4-免改板降本候选-BOM.csv`,'\uFEFF'+upload.map(r=>r.map(q).join(',')).join('\r\n')+'\r\n','utf8');
}
const xlsx=costMode?`${costDir}/DTU-V0.14.4-免改板降本候选-BOM.xlsx`:`${dir}/DTU-V0.14.4-BOM-物料型号封装数量.xlsx`;
await (await SpreadsheetFile.exportXlsx(wb)).save(xlsx);
console.log(JSON.stringify({models:grouped.length,quantity:99,xlsx,totalCell:`D${total}`,source}));
