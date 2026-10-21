from pathlib import Path
exec(Path('PCB/scripts/router-v12.py').read_text(encoding='utf-8'))
load_plan(P/'manifests/rf-routing-v12.json');prior=load_plan(P/'manifests/usb-routing-v12.json');failed=[]
for net,a,b in prior['failed']:
 done=False
 for w in [.2032,.1524,.127]:
  for p,q in [(a,b),(b,a)]:
   if addroute(net,p,q,w,(1,2)):
    print(net,'routed',w,flush=True);done=True;break
  if done:break
 if not done:failed.append([net,a,b]);print('FAILED',net,flush=True)
save_plan('usb-repair-v12',failed)
