"""Map the four DFM mask-opening clearance warnings; no PCB mutation."""
from pathlib import Path
import json,csv,math

root=Path('PCB');M=root/'manifests'
current=json.loads((M/'current-pcb-delivery-v13.json').read_text(encoding='utf8'))
exec((root/'scripts/router-v13.py').read_text(encoding='utf8').replace('read-pcb-pads-v13.json',current['actualPadManifest']))
plan=json.loads((M/current['actualCopperManifest']).read_text(encoding='utf8'))
exec((root/'scripts/render-hy20-gerber-v13.py').read_text(encoding='utf8').split('for label,copper,mask,silk in')[0])
z.close();z=zipfile.ZipFile(current['productionGerber']);cache.clear()
openings=[g for g,dark in geom('Gerber_TopSolderMaskLayer.GTS')[0] if dark]
mask=unary_union(openings)
specs=[('D10','437ee3b0ea55cd34e15','6085135c819a0a52',25),
       ('U1','27e64738f6dde1f7e94','49228cec81f7eb66',20),
       ('U1','27e64738f6dde1f7e89','49228cec81f7eb66',20),
       ('U1','27e64738f6dde1f7e95','49228cec81f7eb66',20)]
rows=[]
for seq,(ref,pid,vid,aperture) in enumerate(specs,1):
    pad=next(q for q in pads if q['id']==pid)
    via=next(q for q in plan['vias'] if q['id']==vid)
    opening=min(openings,key=lambda g:pad['geom'].hausdorff_distance(g))
    assert pad['geom'].hausdorff_distance(opening)<.08
    center=Point(via['x'],via['y'])
    annulus=center.buffer(via['diameter']/2)
    hole=center.buffer(via['hole']/2)
    gap=annulus.distance(opening)
    assert pad['net']==via['net']=='GND'
    assert not annulus.intersects(opening) and not hole.intersects(mask)
    assert .002<gap<.015
    if aperture==25:assert .49<opening.bounds[2]-opening.bounds[0]<.52
    else:assert 1.39<opening.bounds[2]-opening.bounds[0]<1.41
    rows.append({'DFM序号':seq,'位号':ref,'焊盘号':pad['number'],'焊盘ID':pid,
                 '过孔ID':vid,'网络':'GND','DFM开窗对象':f'i274x.RoundRect.d{aperture}',
                 '过孔铜边至此开窗mm':round(gap,6),'DFM显示mm':f'{gap:.2f}',
                 '孔边至此开窗mm':round(center.distance(opening)-via['hole']/2,6),
                 '孔边至全部开窗最小mm':round(center.distance(mask)-via['hole']/2,6),
                 '此开窗与过孔铜盘相交面积mm2':annulus.intersection(opening).area,
                 '顶层孔口盖油':True,'实物工艺已确认':False})
assert [q['DFM显示mm'] for q in rows]==['0.00','0.01','0.01','0.01']
record={'PCBModified':False,'factoryDfmPassed':False,'sourceGerber':current['productionGerber'],
        'DFMExactFourMapped':True,'distinctVias':2,'rows':rows,
        'disposition':'四项均为同网GND盖油过孔的外圈铜接近开窗；名义图形未相交，但盖油对位余量很小。保留当前结构，列为厂家工艺待确认，不视为DFM通过。',
        'relatedReview':'dfm-seven-pad-spacing-locations-v13.json',
        'reasonForNoImmediateMutation':'中央接地孔涉及模组散热/接地结构；不缩小孔环或标准焊盘来消除提示，亦不直接屏蔽规则。',
        'manufacturerSource':'https://m.jlc.com/portal/server_guide_34402.html'}
(M/'dfm-four-opening-clearance-review-v13.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
with (root/'reports/V0.13-四项开窗露线复核.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
table='\n'.join(f"| {q['DFM序号']} | {q['位号']}/{q['焊盘号']} | {q['过孔铜边至此开窗mm']:.6f} | {q['孔边至此开窗mm']:.6f} |" for q in rows)
doc=root/'docs/V0.13-四项开窗露线复核记录.md'
doc.write_text(f'''# V0.13 四项开窗露线复核

2026-10-15。依据用户两张定位图、当前 DFM 界面四行对象及 Maskfix Gerber/实际网表逐项定位。此轮没有修改 PCB、阻焊、钢网、规则阈值或交付 Gerber。

DFM 项目为“阻焊层分析 > 开窗露线”，阈值小于 0.08 mm 为危险。对象 1 的 r17.7165 对应 Ø0.45 mm 的过孔外圈铜；对象 2 分别为 d25 的 D10 接地焊盘开窗和三个 d20 的 ESP32 U1 散热地焊盘开窗。这四项涉及两个过孔，并不是四个独立故障。

| DFM序号 | 位号/引脚 | 过孔外铜边至该开窗mm | 孔边至该开窗mm |
|---|---|---|---|
{table}

所有相关对象均为 GND。几何间隙按两位小数显示正好为 0.00、0.01、0.01、0.01 mm，匹配截图顺序与对象尺寸；“0.00”不代表已经确认有图形相交。四个被标记的开窗与相应过孔铜盘的名义相交面积均为 0，两个过孔的孔口也均未落入任何顶层开窗。将全部开窗纳入核对后，这两个孔的最小孔边盖油余量约 0.127～0.129 mm；不能只采用四个报警对象的距离而漏掉附近同网直连焊盘的开窗。

它们对应先前七项焊盘距焊盘检查中的 D10/2 及 U1 三块 29 号散热地焊盘，是同一批位置在阻焊检查中的另一项提示。没有发现由这四项构成的不同网络短接。

处理状态：名义图形核对完成，制造工艺尚待确认。外圈铜距开窗仅约 4～14 微米，远小于 DFM 的 0.08 mm 预警值，生产对位偏差可能使部分同网铜环露出，因此不能因为孔口盖油或同网就宣称制造检查通过。厂家关于开窗、盖油和对位的要求仍须结合最终生产稿确认。当前保留接地、散热结构，不为消除红色而削小标准模组焊盘、降低过孔孔环、删除散热接地孔或合并开窗。若工厂不接受该盖油余量，应重新设计这两个过孔的引出和位置，并重新核对接地、连接性及阻焊加工。

制造确认范围：确认这两个 Ø0.45/Ø0.20 mm 盖油孔在相邻 GND 开窗旁的实际掩膜与塞/盖油能力，避免对位偏差把孔口打开；不能只回复“都是 GND 没关系”。本记录不等于盖油实物验证、DFM 放行或量产放行。

依据：当前 Maskfix Gerber、mask-fixed-actual-routing-v13.json、mask-fixed-pcb-pads-v13.json、DFM 当前四行对象；厂家说明：https://m.jlc.com/portal/server_guide_34402.html 。逐项唯一 ID、几何值及孔口核对见 JSON/CSV；可复现脚本 audit-exposed-opening-four-v13.py。
''',encoding='utf8')
current['openingClearanceReview']=str(doc.resolve())
current['openDfmItems']=[q for q in current['openDfmItems'] if not q.startswith('开窗露线4项')]+['开窗露线4项已定位：D10/2与ESP32三块散热地焊盘，涉及两个GND过孔；名义未相交、孔口盖油，但外圈余量仅0.004～0.014mm，待厂家工艺确认。']
(M/'current-pcb-delivery-v13.json').write_text(json.dumps(current,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'mappedRows':len(rows),'distinctVias':2,'sameNet':'GND','PCBModified':False,'pairs':rows},ensure_ascii=True))
