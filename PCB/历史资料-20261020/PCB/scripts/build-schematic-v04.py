from pathlib import Path
import json
P=Path('PCB');M=json.loads((P/'manifests/design.json').read_text(encoding='utf-8'));L='0819f05c4eef4c71ace90d822a990e87';cat={}
for f in ['completion-candidates','completion-more','final-passives']:
 for k,a in json.loads((P/f'manifests/{f}.json').read_text(encoding='utf-8'))['result'].items():
  if a:cat[k]=a[0]
def base(u,s,f):return dict(uuid=u,libraryUuid=L,supplierId=s,footprint=f)
V={'10k':base('b948db94476e4027ac8953235755ec96','C25804','R0603'),'100k':base('40ff282b3d594c33b798d1707d8406cb','C25803','R0603'),'1k':base('18db11499a04403ba8c98e2f7a687fbc','C21190','R0603'),'100nF':base('96b39256cc3f4d80bd3b503deb4f3328','C14663','C0603'),'1uF':base('f4744ff7405a46a48e360c2c6fadeca3','C15849','C0603'),'10uF':base('679a610955bc42288af58aa8f87915dc','C14860','C1206'),'22uF':base('fd86deb12afd4f84b2aa16c379f9750a','C441864','C0805'),'ESD':base('b2bd3dcb86d14c9c99d2f9a75ba77a71','C85401','SOD-882'),'SW':base('0ad8dbc3a8644ba08fb62b8dc809ff93','C139797','KEY-SMD_4P')}
for v,k in {'0R':'0603WAF0000T5E','10R':'0603WAF100JT5E','22R':'0603WAF220JT5E','100R':'0603WAF1000T5E','120R':'0603WAF1200T5E','330R':'0603WAF3300T5E','5.1k':'0603WAF5101T5E','1.87k':'0603WAF1871T5E','232k':'0603WAF2323T5E','1M':'0603WAF1004T5E','75k':'0603WAF7502T5E','20k':'0603WAF2002T5E','620k':'0603WAF6203T5E','200k':'0603WAF2003T5E','2.2nF':'CL10B222KB8NNNC','10nF':'CL10B103KB8NNNC','100pF':'CL10C101JB8NNNC','33pF':'CL10C330JB8NNNC','3.3pF':'CL10C3R3BB8NNNC','4.7uF':'CL10A475KO8NNNC','USB':'TYPE-C-31-M-12'}.items():V[v]=cat[k]
N={};A=[];counts={}
def pins(r,m):
 d=N.setdefault(r,{})
 for p,n in m.items():
  p=str(p)
  if p in d:assert d[p]==n,(r,p)
  d[p]=n
def add(r,v,page,a=None,b=None,dnp=False,m=None):
 c=V[v];i=counts.get(page,0);counts[page]=i+1
 display=v if v not in ['ESD','USB','SW'] else {'ESD':'PESD5V0U1UL,315','USB':'TYPE-C-31-M-12','SW':'SKRPACE010'}[v]
 rating={'100nF':'50V','1uF':'16V','10uF':'25V','22uF':'10V','4.7uF':'16V','2.2nF':'50V','10nF':'50V','100pF':'50V','33pF':'50V','3.3pF':'50V'}.get(v,'')
 z=dict(ref=r,value=display,name=display+(' '+rating if rating else '')+(' DNP' if dnp else ''),device=dict(libraryUuid=c['libraryUuid'],uuid=c['uuid']),supplierId=c['supplierId'],footprint=c['footprint'],page=page,x=220+i%6*320,y=900+i//6*130,sub=None,dnp=dnp)
 A.append(z)
 if m is not None:pins(r,m)
 elif a is not None:pins(r,{1:a,2:b})
for r,m in json.loads((P/'manifests/auto-selection-netmap.json').read_text(encoding='utf-8')).items():pins(r,m)
for ms in json.loads((P/'manifests/auto-selection-integration.json').read_text(encoding='utf-8')).values():
 for r,m in ms.items():pins(r,m)
pins('U3',{1:'EFUSE_UVLO',2:'EFUSE_OVLO',4:'POWER_FAULT_N',5:'VIN_OR',6:'VIN_PROT',7:'EFUSE_DVDT',8:'GND',9:'EFUSE_ILM'});pins('D4',{1:'VIN_OR',2:'GND'})
for r,v,a,b in [('R1','232k','VIN_OR','EFUSE_UVLO'),('R2','100k','EFUSE_UVLO','GND'),('R3','1M','VIN_OR','EFUSE_OVLO'),('R4','100k','EFUSE_OVLO','GND'),('R5','1.87k','EFUSE_ILM','GND'),('R6','10k','VDD_3V3','POWER_FAULT_N')]:add(r,v,1,a,b)
for r,v,a in [('C1','10uF','VIN_OR'),('C2','100nF','VIN_OR'),('C3','10uF','VIN_PROT'),('C4','2.2nF','EFUSE_DVDT')]:add(r,v,1,a,'GND')
pins('U1',{1:'GND',2:'VDD_3V3',3:'ESP_EN',6:'MCU_LTE_TX',7:'MCU_LTE_RX',8:'MCU_LTE_PWRKEY',10:'MCU_LTE_RESET',11:'LTE_STATUS_N',12:'LTE_PWR_EN',13:'ESP_USB_DM',14:'ESP_USB_DP',15:'ESP_BOOT',16:'MCU_LTE_CTS',17:'MCU_LTE_RTS',18:'ESP_STRAP27',27:'ESP_STRAP26',28:'GND',29:'GND',30:'GND',32:'GND'})
pins('SW2',{1:'ESP_EN',2:'ESP_EN',3:'GND',4:'GND'});pins('SW3',{1:'ESP_BOOT',2:'ESP_BOOT',3:'GND',4:'GND'})
for r,v,a,b in [('R10','10k','VDD_3V3','ESP_EN'),('R11','10k','VDD_3V3','ESP_BOOT'),('R12','10k','GND','ESP_STRAP26'),('R13','10k','VDD_3V3','ESP_STRAP27'),('R14','100k','LTE_PWR_EN','GND'),('R15','22R','ESP_USB_DP','ESP_USB_DP_EXT'),('R16','22R','ESP_USB_DM','ESP_USB_DM_EXT'),('R17','5.1k','ESP_USB_CC1','GND'),('R18','5.1k','ESP_USB_CC2','GND')]:add(r,v,2,a,b)
for r,v,a in [('C10','1uF','ESP_EN'),('C11','10uF','VDD_3V3'),('C12','100nF','VDD_3V3')]:add(r,v,2,a,'GND')
add('J6','USB',2)
for r,a in [('D18','ESP_USB_DP_EXT'),('D19','ESP_USB_DM_EXT')]:add(r,'ESD',2,m={1:a,2:'GND'})
pins('U2',{7:'LTE_PWRKEY',11:'SIM_DATA_M',12:'SIM_RST_M',13:'SIM_CLK_M',14:'SIM_VDD',15:'LTE_RESET',16:'LTE_NETSTATUS',17:'LTE_RXD',18:'LTE_TXD',19:'GND',22:'LTE_RTS_OUT',23:'LTE_CTS_IN',24:'LTE_VDD_EXT',25:'LTE_STATUS',35:'LTE_ANT',42:'VDD_4G',43:'VDD_4G',59:'LTE_USB_DP',60:'LTE_USB_DM',61:'LTE_USB_VBUS',79:'SIM_DET',82:'LTE_BOOT',99:'LTE_VREF',100:'GND'})
pins('U2',{p:'GND' for p in [1,10,27,34,36,37,40,41,45,46,47,48,70,71,72,73,88,89,90,91,92,93,94,95,103]});pins('C80',{1:'VDD_4G',2:'GND'})
for r,v in [('C81','22uF'),('C82','100nF'),('C83','100pF'),('C84','33pF')]:add(r,v,3,'VDD_4G','GND')
for r,v,a,b in [('R60','0R','LTE_USB_DP','LTE_USB_DP_EXT'),('R61','0R','LTE_USB_DM','LTE_USB_DM_EXT'),('R62','5.1k','LTE_USB_CC1','GND'),('R63','5.1k','LTE_USB_CC2','GND'),('R64','10k','LTE_VDD_EXT','LTE_BOOT_SOURCE')]:add(r,v,3,a,b)
add('SW4','SW',3,m={1:'LTE_BOOT_SOURCE',2:'LTE_BOOT_SOURCE',3:'LTE_BOOT',4:'LTE_BOOT'});add('J7','USB',3)
for r,a in [('D20','LTE_USB_DP_EXT'),('D21','LTE_USB_DM_EXT')]:add(r,'ESD',3,m={1:a,2:'GND'})
pins('J4',{'C1':'SIM_VDD','C2':'SIM_RST','C3':'SIM_CLK','C7':'SIM_DATA','C5':'GND','CD':'SIM_DET',8:'GND',9:'GND',10:'GND',11:'GND'});pins('J5',{1:'GND',2:'LTE_RF_FEED',3:'GND'});pins('D10',{1:'LTE_RF_FEED',2:'GND'})
for r,n in [('D11','SIM_DATA'),('D12','SIM_RST'),('D13','SIM_CLK')]:pins(r,{1:n,2:'GND'})
for r,v,a,b in [('R50','0R','LTE_ANT','LTE_RF_FEED'),('R51','22R','SIM_DATA_M','SIM_DATA'),('R52','22R','SIM_RST_M','SIM_RST'),('R53','22R','SIM_CLK_M','SIM_CLK'),('R54','10k','SIM_VDD','SIM_DATA'),('R55','100k','LTE_VREF','SIM_DET')]:add(r,v,4,a,b)
for r,a in [('C50','LTE_ANT'),('C51','LTE_RF_FEED')]:
 add(r,'1uF',4,a,'GND',True);A[-1].update(name='TUNE DNP',value='TUNE DNP',supplierId='',pending='RF matching value after antenna tuning')
for r,v,a,d in [('C52','100nF','SIM_VDD',False),('C53','100pF','SIM_VDD',False),('C54','10nF','SIM_DET',False),('C55','33pF','SIM_CLK',True)]:add(r,v,4,a,'GND',d)
pins('J1',{3:'RS485_A_EXT',4:'RS485_B_EXT'});pins('J2',{3:'RS232_TX_EXT',4:'RS232_RX_EXT'});pins('J3',{3:'TTL_TX_EXT',4:'TTL_RX_EXT'});pins('U6',{6:'RS485_A',7:'RS485_B'});pins('D5',{1:'RS485_A_EXT',2:'RS485_B_EXT',3:'GND'})
pins('U7',{2:'232_C1P',3:'232_VPLUS',4:'232_C1N',5:'232_C2P',6:'232_C2N',7:'232_VMINUS',8:'232_RIN',10:'232_TOUT'});pins('D6',{1:'RS232_TX_EXT',2:'GND'});pins('D7',{1:'RS232_RX_EXT',2:'GND'});pins('D8',{1:'TTL_TX_EXT',2:'GND'});pins('D9',{1:'TTL_RX_EXT',2:'GND'})
for r,v,a,b,d in [('R30','10R','RS485_A','RS485_A_EXT',False),('R31','10R','RS485_B','RS485_B_EXT',False),('R32','120R','RS485_A_EXT','RS485_B_EXT',True),('R33','100R','232_TOUT','RS232_TX_EXT',False),('R34','100R','RS232_RX_EXT','232_RIN',False),('R35','100R','TTL_TX_BUF','TTL_TX_EXT',False),('R36','330R','TTL_RX_EXT','TTL_RX_BUF',False),('R37','100k','TTL_RX_BUF','GND',False)]:add(r,v,5,a,b,d)
add('R38','10k',5,'VDD_3V3','FIELD_RX')
for r,a,b in [('C30','232_C1P','232_C1N'),('C31','232_C2P','232_C2N'),('C32','232_VPLUS','GND'),('C33','232_VMINUS','GND'),('C34','VDD_3V3','GND'),('C35','VDD_3V3','GND'),('C36','VDD_5V_IF','GND'),('C37','VDD_3V3','GND'),('C38','VDD_3V3','GND')]:add(r,'100nF',5,a,b)
pins('U10',{1:'VDD_3V3',2:'GND',3:'MCU_LTE_TX',4:'MCU_LTE_RX',5:'MCU_LTE_RTS',6:'MCU_LTE_CTS',7:'VDD_3V3',8:'GND',9:'LTE_STATUS_N',10:'GND',11:'LTE_RTS_SER',12:'LTE_CTS_SER',13:'LTE_TX_SER',14:'LTE_RX_SER',15:'VDD_3V3',16:'VDD_3V3'})
for q,b,c in [('Q1','Q1_BASE','LTE_PWRKEY'),('Q2','Q2_BASE','LTE_RESET'),('Q3','Q3_BASE','LTE_STATUS_N'),('Q4','Q4_BASE','LTE_NETSTATUS_N')]:pins(q,{1:b,2:'GND',3:c})
for r,v,a,b in [('R70','10k','MCU_LTE_PWRKEY','Q1_BASE'),('R71','100k','Q1_BASE','GND'),('R72','10k','MCU_LTE_RESET','Q2_BASE'),('R73','100k','Q2_BASE','GND'),('R74','10k','LTE_STATUS','Q3_BASE'),('R75','100k','Q3_BASE','GND'),('R76','10k','VDD_3V3','LTE_STATUS_N'),('R77','10k','LTE_NETSTATUS','Q4_BASE'),('R78','100k','Q4_BASE','GND'),('R79','10k','VDD_3V3','LTE_NETSTATUS_N'),('R80','100k','MCU_LTE_PWRKEY','GND'),('R81','100k','MCU_LTE_RESET','GND'),('R84','1k','LTE_RX_SER','LTE_RXD'),('R85','1k','LTE_TXD','LTE_TX_SER'),('R86','1k','LTE_CTS_SER','LTE_CTS_IN'),('R87','1k','LTE_RTS_OUT','LTE_RTS_SER')]:add(r,v,7,a,b)
add('R82','100k',7,'VDD_3V3','MCU_LTE_RX')
add('R83','100k',7,'MCU_LTE_CTS','GND')
for r in ['C70','C71']:add(r,'100nF',7,'VDD_3V3','GND')
pins('U4',{1:'LTE_FB',2:'LTE_PWR_EN',3:'VIN_PROT',4:'GND',5:'LTE_SW',6:'LTE_BST'});pins('U5',{1:'VDD_3V3',2:'VIN_PROT',3:'VIN_PROT',4:'GND',5:'MCU_SW',6:'MCU_BST'});pins('U11',{1:'TTL_BOOST_SW',2:'GND',3:'TTL_5V_FB',4:'VDD_3V3',5:'VDD_3V3'})
pins('L1',{1:'LTE_SW',2:'VDD_4G'});pins('L2',{1:'MCU_SW',2:'VDD_3V3'});pins('L3',{1:'VDD_3V3',2:'TTL_BOOST_SW'});pins('D14',{1:'VDD_5V_IF',2:'TTL_BOOST_SW'})
for r,v,a,b in [('R90','75k','VDD_4G','LTE_FB'),('R91','20k','LTE_FB','GND'),('R92','620k','VDD_5V_IF','TTL_5V_FB'),('R93','200k','TTL_5V_FB','GND')]:add(r,v,8,a,b)
for r,v,a,b in [('C90','10uF','VIN_PROT','GND'),('C91','100nF','VIN_PROT','GND'),('C92','100nF','LTE_BST','LTE_SW'),('C93','22uF','VDD_4G','GND'),('C94','22uF','VDD_4G','GND'),('C95','100pF','VDD_4G','LTE_FB'),('C96','10uF','VIN_PROT','GND'),('C97','100nF','MCU_BST','MCU_SW'),('C98','22uF','VDD_3V3','GND'),('C99','22uF','VDD_3V3','GND'),('C106','100nF','VIN_PROT','GND'),('C107','4.7uF','VDD_3V3','GND'),('C108','4.7uF','VDD_5V_IF','GND'),('C109','3.3pF','VDD_5V_IF','TTL_5V_FB')]:add(r,v,8,a,b)
for ref,prefix in [('J6','ESP'),('J7','LTE')]:
 pins(ref,{'A1B12':'GND','B1A12':'GND',1:'GND',2:'GND',3:'GND',4:'GND','A6':prefix+'_USB_DP_EXT','B6':prefix+'_USB_DP_EXT','A7':prefix+'_USB_DM_EXT','B7':prefix+'_USB_DM_EXT','A5':prefix+'_USB_CC1','B5':prefix+'_USB_CC2','A4B9':prefix+'_USB_VBUS','B4A9':prefix+'_USB_VBUS'})
parts={z['ref']:z for z in M['parts']};parts['U3'].update(device=dict(libraryUuid=L,uuid='676a12fadece41eb8224bb38360970ca'),name='TPS259470ARPWR',supplierId='C3662799',footprint='VQFN-10_L2.0-W2.0-P0.45-TL',x=780,y=340)
for z in A:parts[z['ref']]=z
M.update(parts=list(parts.values()),revision='V0.4');(P/'manifests/design.json').write_text(json.dumps(M,ensure_ascii=False,indent=2),encoding='utf-8');(P/'manifests/full-schematic-netmap.json').write_text(json.dumps(N,indent=2),encoding='utf-8')
guard='const p=await eda.dmt_Project.getCurrentProjectInfo();if(p?.uuid!=='+json.dumps(M['projectUuid'])+')throw Error("Wrong project");'
for page in M['pages']:
 i=page['index'];u=page['uuid'];pg=guard+f'if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="{u}")throw Error("Wrong page");'
 (P/f'scripts/open-v04-{i}.js').write_text(guard+f'await eda.dmt_EditorControl.openDocument("{u}");return await eda.dmt_SelectControl.getCurrentDocumentInfo();',encoding='utf-8')
 ss=[z for z in A if z['page']==i]
 for k in range(0,len(ss),8):
  s='const spec='+json.dumps(ss[k:k+8])+';'+pg+'const existing=await eda.sch_PrimitiveComponent.getAll("part");const out=[];for(const z of spec){let c=existing.find(t=>t.getState_Designator()===z.ref);if(!c)c=await eda.sch_PrimitiveComponent.create(z.device,z.x,z.y,undefined,0,false,!z.dnp,true);if(!c)throw Error("Cannot create "+z.ref);const a=c.toAsync();a.setState_Designator(z.ref);if(!c.getState_UniqueId())a.setState_UniqueId("dtu_"+z.ref.toLowerCase());a.setState_Name(z.name);if(z.dnp)a.setState_AddIntoBom(false);if(z.pending){a.setState_ManufacturerId("");a.setState_SupplierId("");a.setState_OtherProperty({...c.getState_OtherProperty(),"Manufacturer Part":"","Supplier Part":"","Value":z.value,"BOM Status":z.pending});}await a.done();out.push(z.ref);}return {saved:await eda.sch_Document.save(),parts:out};'
  (P/f'scripts/place-v04-{i}-{k//8+1}.js').write_text(s,encoding='utf-8')
 (P/f'scripts/read-v04-{i}.js').write_text(pg+(P/'scripts/read-selector-pins.js').read_text(encoding='utf-8'),encoding='utf-8')
 (P/f'scripts/unique-v04-{i}.js').write_text(pg+'const groups={};for(const c of await eda.sch_PrimitiveComponent.getAll("part")){const r=c.getState_Designator();(groups[r]??=[]).push(c);}for(const [r,cs]of Object.entries(groups)){const uid=cs.map(c=>c.getState_UniqueId()).find(Boolean)||"dtu_"+r.toLowerCase();for(const c of cs)if(c.getState_UniqueId()!==uid){const a=c.toAsync();a.setState_UniqueId(uid);await a.done();}}return {saved:await eda.sch_Document.save()};',encoding='utf-8')
 rr=[z['ref']for z in M['parts']if z['page']==i]+(['U1']if i==2 else ['U2']if i==3 else [])
 for k in range(0,len(rr),10):
  rs=rr[k:k+10];ns={r:N[r]for r in rs if r in N}
  for name in ['wire','style']:
   t=(P/f'scripts/{name}-selection-integration-5.js').read_text(encoding='utf-8');t=t[t.index('const p='):].replace('await eda.dmt_EditorControl.openDocument("31c8ed08a1998d0d");','').replace('31c8ed08a1998d0d',u)
   (P/f'scripts/{name}-v04-{i}-{k//10+1}.js').write_text('const refs='+json.dumps(rs)+';const map='+json.dumps(ns)+';'+t,encoding='utf-8')
print(json.dumps({'newParts':len(A),'physicalParts':len(M['parts'])+2,'mappedPins':sum(map(len,N.values()))}))
