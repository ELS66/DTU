"""Rebuild affected pages with separated symbol cells to avoid geometric net merges."""
from pathlib import Path
exec(Path('PCB/scripts/prepare-schematic-v12.py').read_text(encoding='utf-8'))
for page in [3,4,7,8]:
    original=[r for r,c in parts.items() if c['props'].get('Channel ID','').startswith('$'+str(page)) and r not in remove]
    fresh={s['ref']:s for s in replacements[page]}
    refs=original+[r for r in fresh if r not in original]
    specs=[]
    if page==3:
        refs.remove('U2');u=fresh['U2'];u['x']=350;u['y']=800;specs.append(u)
    for i,ref in enumerate(refs):
        x=(850 if page==3 else 350)+(i%4)*350;y=450+(i//4)*250
        s=copy.deepcopy(fresh[ref]) if ref in fresh else spec(ref,ref,x,y)
        s['x']=x;s['y']=y;specs.append(s)
    code=f"if((await eda.dmt_Project.getCurrentProjectInfo())?.uuid!=={js(PROJECT)}||(await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=={js(pages[page])})throw Error('Wrong project/page');"+helpers
    code+="const wireIds=await eda.sch_PrimitiveWire.getAllPrimitiveId();if(wireIds.length&&!await eda.sch_PrimitiveWire.delete(wireIds))throw Error('Wires deletion failed');const cs=await eda.sch_PrimitiveComponent.getAll();if(cs.length&&!await eda.sch_PrimitiveComponent.delete(cs))throw Error('Components deletion failed');const ts=await eda.sch_PrimitiveText.getAllPrimitiveId();if(ts.length&&!await eda.sch_PrimitiveText.delete(ts))throw Error('Text deletion failed');"
    code+='const specs='+js(specs)+';for(const s of specs)await create(s);'
    code+=f"await eda.sch_PrimitiveText.create(180,170,{js(notes[page])},0,null,null,13);return {{saved:await eda.sch_Document.save(),refs:(await eda.sch_PrimitiveComponent.getAll('part')).map(c=>c.getState_Designator())}};"
    (P/f'scripts/rebuild-schematic-page{page}-v12.js').write_text(code,encoding='utf-8')
    (P/f'scripts/activate-schematic-page{page}-v12.js').write_text(f"if((await eda.dmt_Project.getCurrentProjectInfo())?.uuid!=={js(PROJECT)})throw Error('Wrong project');return await eda.dmt_EditorControl.openDocument({js(pages[page])});",encoding='utf-8')
print('Rebuild pages prepared')
