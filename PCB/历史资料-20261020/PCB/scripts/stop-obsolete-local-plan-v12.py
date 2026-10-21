import psutil
targets=[]
for p in psutil.process_iter(['pid','name','cmdline']):
 try:
  args=p.info['cmdline'] or []
  if p.info['name'].lower()=='python.exe' and any(a.replace('\\','/').endswith('PCB/scripts/plan-pass3-repair-large-v12.py') for a in args):targets.append(p)
 except (psutil.AccessDenied,psutil.NoSuchProcess):pass
for p in targets:
 print('Stopping only obsolete local PCB planner',p.pid,p.cmdline());p.terminate()
