from pathlib import Path
import json,csv
root=Path('PCB');M=root/'manifests';D=root/'docs'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')
pairs=load(M/'dfm-pad-spacing-pairs-v13.json');assessment=load(M/'dfm-pad-spacing-final-assessment-v13.json');vm={v['via']:v for v in assessment['vias']}
specs=[(1,'D9','2','74a721a974fa8d8f','d4a61923be0d68fce19'),(2,'C33','2','a9b9ba87672a2edf','ffa9cbcae70ecc33e14'),(3,'D10','2','6085135c819a0a52','437ee3b0ea55cd34e15'),(4,'U1','29','49228cec81f7eb66','27e64738f6dde1f7e94'),(5,'U1','29','49228cec81f7eb66','27e64738f6dde1f7e89'),(6,'U1','29','49228cec81f7eb66','27e64738f6dde1f7e95'),(7,'U2','82','b4203b25c2e281b8','9a20c59b6357d964e141')]
rows=[]
for seq,ref,pin,via,pid in specs:
 pair=next(p for p in pairs if p['a']['ref']==via and p['b']['id']==pid);mask=vm[via]
 assert pair['sameNet'] and not mask['holeExposed']
 rows.append({'序号':seq,'位号':ref,'引脚':pin,'网络':pair['b']['net'],'铜间距mm':round(pair['gapMm'],5),'DFM显示mm':f"{pair['gapMm']:.2f}",'孔口盖油':'是','过孔ID':via,'焊盘ID':pid,'孔边到阻焊开窗mm':round(mask['holeToMaskOpeningGapMm'],5),'结论':'同网、孔口盖油；保留设计并由厂家确认盖油工艺'})
assert sum(r['网络']=='GND' for r in rows)==6 and rows[-1]['网络']=='LTE_BOOT'
save(M/'dfm-seven-pad-spacing-locations-v13.json',{'source':'用户三张定位图与当前NPTHfix Gerber/网表逐项比对','DFMSevenLocationsMapped':True,'rows':rows,'PCBModified':False,'factoryDfmPassed':False})
with (root/'reports/V0.13-七项焊盘间距复核.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
table='\n'.join(f"| {r['序号']} | {r['位号']} / {r['引脚']} | {r['网络']} | {r['铜间距mm']:.3f} |" for r in rows)
report=f'''# V0.13 七项焊盘间距定位复核

2026-10-15。依据用户补充的三张定位图，当前七项危险已逐条对应到 NPTHfix 工程和实际 Gerber；此轮未改 PCB、阻焊、钢网或检查阈值。

| DFM序号 | 位号/引脚 | 网络 | 铜间距（约mm） |
|---|---|---|---|
{table}

第三张图定位了 C33 与 D9；第二张图定位了 D10 与 U2 的 BOOT；第一张图为 U1 九宫格散热地中央同一个过孔与另外三块地焊盘之间的三条距离，不能算成三组独立信号间隙。每一条都是焊盘与同一网络过孔铜盘的接近关系，未对应到不同网络的短路间隙。

五个相关过孔的孔口在生产 Gerber 中全部由顶层阻焊覆盖。孔边到最近阻焊开窗的间距为 {min(r['孔边到阻焊开窗mm'] for r in rows):.3f}～{max(r['孔边到阻焊开窗mm'] for r in rows):.3f} mm。铜盘边缘距离与孔口是否露铜不同，实际是否满足盖油、塞油和焊接工艺仍由厂家核对；本记录不宣称盖油效果已经实物验证。

处理结论：保留当前同网接地、BOOT 引出和散热结构；将这七项登记为已定位的同网盖油过孔提示，供工厂按具体工艺确认。没有移动或删除散热过孔、缩小标准模组焊盘、增设铜桥或屏蔽 DFM 规则。整板其他 DFM 项目和首板验证仍未完成。

可复现依据：`dfm-seven-pad-spacing-locations-v13.json`、`V0.13-七项焊盘间距复核.csv`。间距计算使用焊盘唯一 ID 区分 U1 上多个同号 29 焊盘，避免重复编号造成位置混淆；`audit-dfm-padspacing-v13.py` 为当前复核脚本。旧的仅凭形状猜测/铜岛候选记录由本条目取代。

厂家布局资料参照：https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c5/pcb-layout-design.html
'''
(D/'V0.13-焊盘距焊盘提示复核记录.md').write_text(report,encoding='utf8')
for n in ['dfm-pad-spacing-mask-assessment-v13.json','dfm-all-near-pads-mask-assessment-v13.json']:
 p=M/n;m=load(p);m['supersededBy']='dfm-pad-spacing-final-assessment-v13.json; dfm-seven-pad-spacing-locations-v13.json';m['DFMExactSevenNotConfirmed']=False;save(p,m)
p=M/'current-pcb-delivery-v13.json';m=load(p);m['openDfmItems']=[s for s in m.get('openDfmItems',[]) if not s.startswith('焊盘距焊盘7项')]+['焊盘距焊盘7项已逐条定位：6项GND、1项LTE_BOOT，均同网且孔口盖油；由厂家确认盖油工艺接受条件'];m['padSpacingReview']=str((D/'V0.13-焊盘距焊盘提示复核记录.md').resolve());save(p,m)
print(json.dumps({'mappedRows':len(rows),'GND':6,'LTE_BOOT':1,'PCBModified':False,'report':str(D/'V0.13-焊盘距焊盘提示复核记录.md'),'maskClearancesMm':[r['孔边到阻焊开窗mm'] for r in rows]},ensure_ascii=True))
