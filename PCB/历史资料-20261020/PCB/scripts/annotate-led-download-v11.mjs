import fs from 'node:fs';
const base='PCB/reports/PCB-V0.11-接口精简';
const png=fs.readFileSync(base+'.png').toString('base64');
const pcb=JSON.parse(fs.readFileSync('PCB/manifests/pcb-pads-interface-v11.json','utf8').replace(/^\uFEFF/,'' )).result;
const pos=Object.fromEntries(pcb.map(c=>[c.ref,[450+c.x*.0254*(500/60),775-c.y*.0254*(585/70)]]));
const parts=[];
const esc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;');
function text(x,y,s,size=24,color='#172536',weight=600){parts.push(`<text x="${x}" y="${y}" font-size="${size}" fill="${color}" font-weight="${weight}">${esc(s)}</text>`);}
function box(x,y,w,label,color){parts.push(`<rect x="${x}" y="${y}" width="${w}" height="45" rx="8" fill="white" stroke="${color}" stroke-width="2"/>`);text(x+13,y+30,label,23,color);}
function line(points,color){parts.push(`<polyline points="${points.map(p=>p.join(',')).join(' ')}" fill="none" stroke="white" stroke-width="7" stroke-linejoin="round"/><polyline points="${points.map(p=>p.join(',')).join(' ')}" fill="none" stroke="${color}" stroke-width="3" stroke-linejoin="round"/>`);}
function ring(ref,color){const [x,y]=pos[ref];parts.push(`<circle cx="${x}" cy="${y}" r="8" fill="none" stroke="white" stroke-width="5"/><circle cx="${x}" cy="${y}" r="8" fill="none" stroke="${color}" stroke-width="3"/>`);}
text(450,57,'V0.11 指示灯与下载口位置',32);
const leds=[['D30','ESP 红灯','#d83939',70,214],['D31','ESP 绿灯','#19854b',70,276],['D32','ESP 蓝灯','#245ccd',70,338],['D33','LTE 红灯','#d83939',1040,405],['D34','LTE 绿灯','#19854b',1040,467],['D35','LTE 蓝灯','#245ccd',1040,529]];
for(const [ref,label,color,x,y] of leds){box(x,y,265,ref+' · '+label,color);const [px,py]=pos[ref];line(x<450?[[x+265,y+22],[420,y+22],[px-10,py]]:[[x,y+22],[980,y+22],[px+10,py]],color);ring(ref,color);}
const cyan='#007f98';
parts.push(`<rect x="503" y="220" width="107" height="23" rx="5" fill="none" stroke="white" stroke-width="6"/><rect x="503" y="220" width="107" height="23" rx="5" fill="none" stroke="${cyan}" stroke-width="3"/>`);
parts.push(`<rect x="737" y="207" width="111" height="23" rx="5" fill="none" stroke="white" stroke-width="6"/><rect x="737" y="207" width="111" height="23" rx="5" fill="none" stroke="${cyan}" stroke-width="3"/>`);
box(390,132,330,'J6 · ESP32 下载口（5孔）',cyan);line([[555,177],[555,216]],cyan);
box(710,79,385,'J7 · Air780EPT 下载口（5孔）',cyan);line([[790,124],[790,203]],cyan);
box(1020,132,335,'D36 · TX 发送灯（绿）','#19854b');line([[1020,154],[975,154],[pos.D36[0],154],[pos.D36[0],pos.D36[1]-10]],'#19854b');ring('D36','#19854b');
box(1040,244,335,'D37 · RX 接收灯（蓝）','#245ccd');line([[1040,266],[985,266],[pos.D37[0]+10,pos.D37[1]]],'#245ccd');ring('D37','#245ccd');
text(450,812,'下方三个端子：RS485 ／ RS232 ／ TTL',22);
text(160,855,'红、绿、蓝灯的状态含义由程序定义；J6/J7 默认保留裸焊孔，两个下载口脚位不同。',22,'#536170',400);
const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="1450" height="890" viewBox="0 0 1450 890"><defs><clipPath id="board"><rect x="450" y="190" width="500" height="585"/></clipPath></defs><rect width="1450" height="890" fill="#f5f7fa"/><g font-family="Microsoft YaHei, sans-serif"><image x="92" y="159" width="1195" height="667" href="data:image/png;base64,${png}" clip-path="url(#board)"/>${parts.join('')}</g></svg>`;
fs.writeFileSync(base+'-灯与下载口标注.svg',svg);
fs.writeFileSync(base+'-灯与下载口标注.html','<!doctype html><meta charset="utf-8"><style>html,body{margin:0;width:1450px;height:890px;overflow:hidden}svg{display:block}</style>'+svg);
fs.writeFileSync('PCB/reports/灯与下载口标注坐标-V0.11.json',JSON.stringify({source:'PCB-V0.11-接口精简.png',positions:Object.fromEntries(['D30','D31','D32','D33','D34','D35','D36','D37','J6','J7'].map(r=>[r,pos[r]]))},null,2));
console.log('SVG annotation generated from PCB component coordinates');
