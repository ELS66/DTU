import json
from pathlib import Path
p=Path('PCB');v=json.loads((p/'manifests/revision-v05.json').read_text());m=v['expected'];rm=['Q5','Q6','R118','R119','R120','R122','R123']
for r in rm:m.pop(r)
m['U8']={'1':'VDD_3V3','2':'GND','3':'FIELD_TX','4':'TTL_TX_BUF','5':'VDD_3V3','6':'VDD_5V_IF'}
m['U6']['3']='MCU_485_DE';m['R121']['1']='MCU_485_DE';m['U14']['11']='RS232_VSENSE';m['U14']['13']='232_FORCEON';m['R37']['2']='VDD_3V3'
v.update(version='V0.6',removedThisRevision=rm,removed=v['removed']+rm,beforeCount=180,plannedCount=173,dnp=['J6','J7','R32','C50','C51','C55']);(p/'manifests/revision-v06.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
base='if((await eda.dmt_Project.getCurrentProjectInfo())?.uuid!=="b7122aadd3e496b681150192bfbef370394a2ba91164cb1621df30a137bdfaf5")throw Error("Wrong project");'
s=(p/'scripts/revise-selector-v05.js').read_text(encoding='utf-8-sig');clear=s[s.index('const parts=await'):s.index('for(const c of parts){const ref=')];wire=s[s.index('for(const c of parts){const ref='):s.index('return {saved:')]
for page,refs,remove in [('8902a3019bd8d84c',['U14','R121'],rm),('31c8ed08a1998d0d',['U6','U8','R37'],['U8'])]:
 setup='';finish=''
 if remove==['U8']:
  refs+=['U8_NEW'];setup='const old=(await eda.sch_PrimitiveComponent.getAll("part")).find(c=>c.getState_Designator()==="U8");const neo=(await eda.sch_PrimitiveComponent.getAll("part")).find(c=>c.getState_Designator()==="U8_NEW");if(!old||!neo)throw Error("Missing pair");const uid=old.getState_UniqueId();'
  finish='const a=neo.toAsync();a.setState_Designator("U8");a.setState_UniqueId(uid);await a.done();const live=await eda.sch_PrimitiveComponent.getAll("part");'
 code=base+'await eda.dmt_EditorControl.openDocument('+json.dumps(page)+');const refs='+json.dumps(refs)+';const remove='+json.dumps(remove)+';const map='+json.dumps({r:m.get(r,{}) for r in refs})+';'+setup+clear+finish+(wire.replace('of parts','of live') if finish else wire)+'return {saved:await eda.sch_Document.save(),removed:remove};'
 (p/f'scripts/revise-{page}-v06.js').write_text(code,encoding='utf-8')
for src,dst in [('export-full-schematic-v04.js','export-full-schematic-v06.js'),('check-schematic-erc-v04.js','check-schematic-erc-v06.js')]:
 (p/'scripts'/dst).write_text((p/'scripts'/src).read_text(encoding='utf-8-sig').replace('v04','v06'),encoding='utf-8')
