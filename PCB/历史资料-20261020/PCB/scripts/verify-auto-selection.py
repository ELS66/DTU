from pathlib import Path
import itertools,json,collections
root=Path(__file__).resolve().parents[1]
n=json.loads((root/'reports/auto-selector.net').read_text(encoding='utf-8'))
items=list(n['components'].items());refs=[c['props']['Designator'] for _,c in items]
assert len(refs)==len(set(refs)), 'Duplicate physical designators'
assert all(uid and c['props'].get('Unique ID') for uid,c in items), 'Blank export identifier'
c={x['props']['Designator']:x for _,x in items}
manifest=json.loads((root/'manifests/design.json').read_text(encoding='utf-8'))
expected_refs={z['ref'] for z in manifest['parts']}|{'U1','U2'}
assert set(c)==expected_refs, f'Missing/extra physical components: {expected_refs-set(c)} / {set(c)-expected_refs}'
assert 'SW1' not in c, 'Manual selector must be removed'
def net(ref,pin):return c[ref]['pinInfoMap'][str(pin)]['net']
expected=json.loads((root/'manifests/auto-selection-netmap.json').read_text(encoding='utf-8'))
for m in json.loads((root/'manifests/auto-selection-integration.json').read_text(encoding='utf-8')).values():
 for ref,pins in m.items():
  if ref in expected:assert expected[ref]==pins
  expected[ref]=pins
checks=0
for ref,pins in expected.items():
 for pin,want in pins.items():
  assert net(ref,pin)==want,f'{ref}:{pin} expected {want}, exported {net(ref,pin)}'
  checks+=1
for ref,mpn,sku in [('R100','0603WAF1502T5E','C22809'),('R106','0603WAF1502T5E','C22809'),('R112','0603WAF1502T5E','C22809'),('R101','0603WAF1001T5E','C21190'),('R107','0603WAF1001T5E','C21190'),('R113','0603WAF1001T5E','C21190')]:
 assert c[ref]['props']['Manufacturer Part']==mpn and c[ref]['props']['Supplier Part']==sku, f'Wrong sense divider SKU: {ref}'
assert len(c['U14']['pinInfoMap'])==14,'Comparator subparts must merge to one 14-pin device'
assert len(c['U2']['pinInfoMap'])==109,'LTE subparts must merge to one 109-pin device'
for j,f,d,r,raw,fused in [('J1','F1','D1','R112','VIN_485','VIN_485_FUSED'),('J2','F2','D2','R106','VIN_232','VIN_232_FUSED'),('J3','F3','D3','R100','VIN_TTL','VIN_TTL_FUSED')]:
 assert net(j,1)==net(f,1)==raw
 assert net(f,2)==net(d,2)==net(r,1)==fused
 assert fused!=net(d,1)=='VIN_OR'
assert len({net('J1',1),net('J2',1),net('J3',1)})==3
assert net('U6',1)==net('U7',9)==net('U12',4)==net('U1',23)=='FIELD_RX'
assert net('U8',6)=='','Unused AXP group must not drive FIELD_RX'
assert net('U8',14)=='VDD_3V3','Unused AXP group must be disabled'
# The model reads encoder input allocation and decoder output allocation from exported pins.
encoder=c['U13']['pinInfoMap'];decoder=c['U9']['pinInfoMap']
input_nets={int(p['name']):p['net'] for p in encoder.values() if p['name'].isdigit()}
output_for_y={int(p['name'].replace('#1Y','')):p['net'] for p in decoder.values() if p['name'].startswith('#1Y')}
port_for_net={'MODE_TTL_N':'TTL','MODE232_N':'RS232','MODE485_N':'RS485'}
source={'TTL_PRESENT_N':'TTL','RS232_PRESENT_N':'RS232','RS485_PRESENT_N':'RS485'}
a0=next(p['net'] for p in encoder.values() if p['name']=='A0');a1=next(p['net'] for p in encoder.values() if p['name']=='A1');gs=next(p['net'] for p in encoder.values() if p['name']=='GS')
assert net('U9',2)==a0 and net('U9',3)==a1 and net('U9',1)==gs
rows=[]
for enabled in (0,1):
 for ttl,rs232,rs485 in itertools.product((0,1),repeat=3):
  present={'TTL':ttl,'RS232':rs232,'RS485':rs485}
  lows=[i for i,signal in input_nets.items() if signal in source and present[source[signal]]]
  winner=max(lows) if enabled and lows else None
  address=((~winner)&7) if winner is not None else 7
  selected=port_for_net.get(output_for_y.get(address&3,''),'OFF') if winner is not None else 'OFF'
  want=('TTL' if ttl else 'RS232' if rs232 else 'RS485' if rs485 else 'OFF') if enabled else 'OFF'
  assert selected==want,f'Priority failed {present}, enable={enabled}: {selected} != {want}'
  rows.append({'enabled':enabled,**present,'selected':selected,'encoderWinner':winner,'activeLowEnables':int(selected!='OFF')})
# Nominal divider/feedback calculation, separate from digital selection truth table.
rt,rb,rf,rpu=124000,10000,910000,4700
factor=(15000+1000)/1000
rising=3.3*(1/rt+1/(rf+rpu))/(1/rt+1/rb+1/(rf+rpu))*factor
falling=(3.3/rt+0.11/rf)/(1/rt+1/rb+1/rf)*factor
report={'status':'PASS','scope':'Exported schematic nets and steady-state logic model; no ERC/DRC or physical circuit test','projectUuid':n['projectId'],'physicalComponents':len(c),'pinNetAssertions':checks,'cases':rows,'nominalDetection':{'risingV':rising,'fallingV':falling,'rcSeconds':(15000*1000/(15000+1000))*100e-9}}
(root/'reports/auto-selection-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='cases'},ensure_ascii=True))
