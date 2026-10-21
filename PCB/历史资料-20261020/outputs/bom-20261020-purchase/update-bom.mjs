import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {FileBlob, SpreadsheetFile} from '@oai/artifact-tool';

const dir='D:/DTU/outputs/bom-20261020-purchase';
const source='D:/DTU/outputs/bom-20261019/DTU-V0.14.4-BOM-物料型号封装数量.xlsx';
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(source));
const s=wb.worksheets.getItemAt(0);
const before=s.getRange('A5:D54').values;
assert.deepEqual(before[0],['物料类型','完整型号','封装','数量']);
assert.equal(before.slice(1,49).reduce((n,r)=>n+r[3],0),99);
if(process.argv.includes('--preview')){
  const blob=await wb.render({sheetName:s.name,range:'A1:D15',scale:1.2,format:'png'});
  await fs.writeFile(`${dir}/before.png`,new Uint8Array(await blob.arrayBuffer()));
  console.log((await wb.inspect({kind:'table',range:`${s.name}!A5:D9`,include:'values,formulas',tableMaxRows:5,tableMaxCols:4,maxChars:1500})).ndjson);
  process.exit(0);
}
const mapping=JSON.parse(await fs.readFile('D:/DTU/outputs/bom-review-20261020/order-bom-mapping.json','utf8'));
const byOld=new Map(mapping.map(d=>[d.original,d]));
assert.equal(byOld.size,48);
const rows=before.slice(1,49).map((r,i)=>{
  const d=byOld.get(r[1]); assert.ok(d,`Missing ${r[1]}`); assert.equal(r[3],d.per_board);
  const o={...d,excelRow:i+6,type:r[0],package:r[2]};
  if([17,18,19,20].includes(d.row))o.package='0603×4，8脚（尺寸待核）';
  if(d.row===5)o.package='立贴4P，P=2mm（尺寸待核）';
  if(d.row===4)o.package='一代三焊脚（尺寸待核）';
  if(d.row===47)o.package='TSOT-23-6';
  if(d.row===16)o.package='SOIC-8';
  if(d.row===39){o.status='本次验证使用橙色';o.note='用户已确认本次使用橙色；下次恢复红色19-217/R6C-AL1M2VY/3T。'}
  else if([4,5,17,18,19,20,41].includes(d.row)){o.status='尺寸或数据表待核';o.note=d.status;}
  else if([13,42].includes(d.row)){o.status='品牌替换待来料核对';o.note=d.status;}
  else if(d.row===47){o.status='首板电源验证待完成';o.note='候选替料，非已验证直接替换；需测启动、纹波、LTE发射负载突变、温升。'}
  else if(d.row===16){o.status='引脚封装匹配，待首板测试';o.note='3.3V±5%供电，首板验证RS485收发与使能切换。'}
  else {o.status=d.status.startsWith('同型号')?'原型号':'已核对规格';o.note=d.status;}
  return o;
});
assert.equal(new Set(rows.flatMap(r=>r.refs.split(','))).size,99);
s.getRange('A2').values=[['DTU V0.14.4 本次采购验证 BOM']];
s.getRange('A3').values=[['48种物料，数量为单板用量，包含U2。橙灯用于本次验证，下次恢复红色。']];
s.getRange('A4').values=[['尺寸和首板待验证项见“替料与验证”，本表不代表这些项目已通过验证。']];
s.getRange('A4').format.font={name:'Arial',size:10,color:'#9A5A12'};
s.getRange('A4:D4').format.rowHeight=23;
for(const r of rows){
  s.getRange(`B${r.excelRow}:C${r.excelRow}`).values=[[r.new,r.package]];
  if(/待/.test(r.status))s.getRange(`B${r.excelRow}:C${r.excelRow}`).format.fill='#FFF1C2';
}
// The original four column layout, row order and single-board quantities are retained.
const detail=wb.worksheets.add('替料与验证');
detail.showGridLines=false;
detail.getRange('A1:H62').format.font={name:'Arial',size:11,color:'#1F2937'};
detail.getRange('A1:H62').format.verticalAlignment='center';
detail.getRange('A2').values=[['本次采购与原 BOM 对照']];
detail.getRange('A2').format.font={name:'Arial',size:15,bold:true};
detail.getRange('A3').values=[['生产5块，原PCB及焊盘保持不变；未验证项目保留具体核对要求。']];
detail.getRange('A5:H5').values=[['位号','原完整型号','本次采购型号/规格','单板数量','5板用量','采购只数','验证状态','备注']];
detail.getRange('A6:H53').values=rows.map(r=>[r.refs,r.original,r.new,r.per_board,null,r.pieces,r.status,r.note]);
for(let i=6;i<=53;i++)detail.getRange(`E${i}`).formulas=[[`=D${i}*5`]];
detail.tables.add('A5:H53',true,'PurchaseBomReview').showFilterButton=true;
detail.getRange('A5:H5').format={fill:'#243C5A',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',verticalAlignment:'center',rowHeight:30};
detail.getRange('A5:H5').format.borders={insideVertical:{style:'thin',color:'#FFFFFF'}};
detail.getRange('A6:H53').format.wrapText=true;
detail.getRange('A6:H53').format.rowHeight=58;
for(const [col,width] of [['A',220],['B',275],['C',340],['D',90],['E',90],['F',90],['G',230],['H',500]])detail.getRange(`${col}1:${col}62`).format.columnWidthPx=width;
detail.getRange('D6:F54').setNumberFormat('#,##0');
detail.getRange('D6:F54').format.horizontalAlignment='right';
detail.getRange('A54').values=[['贴装总数量']];
detail.getRange('D54:E54').formulas=[['=SUM(D6:D53)','=SUM(E6:E53)']];
detail.getRange('A54:H54').format={fill:'#E8EDF4',font:{name:'Arial',size:11,bold:true},rowHeight:30};
detail.getRange('G6:G53').conditionalFormats.add('containsText',{text:'待',format:{fill:'#FFF1C2',font:{color:'#8C4B00'}}});
detail.getRange('A57').values=[['来源']];
detail.getRange('B57').values=[['2026-10-20更新采购订单：订单数据 (1).xlsx；数量按已选款式/标题的包装数换算。']];
detail.getRange('B58').values=[['基准：V0.14.4 Threefix-BOM-99.csv；原完整型号来自2026-10-19型号汇总。']];
detail.getRange('B59').values=[['J1/J2/J3、J5、通用排阻需要尺寸/连接图；CJ SMF12CA需要准确厂商数据表。']];
detail.getRange('B60').values=[['U4 SCT2330TVBR需首板验证，不能仅按相同引脚视为已经验证等效。']];
detail.getRange('B61').values=[['U2实际装配ML307R-DL；DFM暂时排除不影响本次装配数量。']];
detail.getRange('B62').values=[['原制造BOM、Gerber和PCB工程未覆盖；本文件用于本次采购及验证装配。']];
detail.getRange('B57:H62').format.wrapText=false;
detail.freezePanes.freezeRows(5);
wb.recalculate();
assert.equal(s.getRange('D54').values[0][0],99);
assert.equal(detail.getRange('D54').values[0][0],99);
assert.equal(detail.getRange('E54').values[0][0],495);
assert.deepEqual(s.getRange('A5:D5').values,before.slice(0,1));
for(let i=0;i<48;i++){
 assert.equal(s.getRange(`A${i+6}`).values[0][0],before[i+1][0]);
 assert.equal(s.getRange(`D${i+6}`).values[0][0],before[i+1][3]);
 assert.equal(detail.getRange(`E${i+6}`).values[0][0],rows[i].need);
}
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!',options:{useRegex:true,maxResults:10},maxChars:1000})).ndjson);
for(const [sheet,range,name] of [[s,'A1:D54','bom'],[detail,'A1:H15','review-top'],[detail,'A40:H54','review-bottom']]){
 const b=await wb.render({sheetName:sheet.name,range,scale:1,format:'png'});
 await fs.writeFile(`${dir}/${name}.png`,new Uint8Array(await b.arrayBuffer()));
}
const output=`${dir}/DTU-V0.14.4-BOM-本次采购验证版-20261020.xlsx`;
await(await SpreadsheetFile.exportXlsx(wb)).save(output);
await fs.writeFile(`${dir}/final-mapping.json`,JSON.stringify(rows,null,2));
console.log(JSON.stringify({output,groups:rows.length,perBoard:99,fiveBoards:495,orange:rows.find(r=>r.row===39).refs}));
