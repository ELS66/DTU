exec(open('PCB/scripts/plan-usb-core-v07.py',encoding='utf-8-sig').read().split('for label,nets,layer,ends')[0])
nets=['LTE_USB_DP_EXT','LTE_USB_DM_EXT'];obs=unary_union([p['geom'] for p in pads if p['net'] not in nets and p['layer'] in [1,12]]+[t['geom'] for t in tracks if t['net'] not in nets and t['layer']==1]+[Point(v['x'],v['y']).buffer(v['diameter']/2) for v in vias if v['net'] not in nets]);m=maskgeom(obs,.51)
for z in [(54.4,34.3),(39.9,68.6)]:
 print('endpoint',z,'clear',Point(*z).distance(obs),'mask',m[round(z[1]/step),round(z[0]/step)])
 if m[round(z[1]/step),round(z[0]/step)]:continue
 s=tuple(round(v/step) for v in z);todo=collections.deque([s]);seen={s}
 while todo:
  x,y=todo.popleft()
  for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
   v=x+dx,y+dy
   if v not in seen and 0<v[0]<nx-1 and 0<v[1]<ny-1 and not m[v[1],v[0]]:seen.add(v);todo.append(v)
 print('reachable',len(seen),[min(x for x,y in seen)*step,min(y for x,y in seen)*step,max(x for x,y in seen)*step,max(y for x,y in seen)*step])
for ref in ['C100','C102']:
 print(ref,[(p['number'],p['net'],p['x'],p['y']) for p in pads if p['ref']==ref])
