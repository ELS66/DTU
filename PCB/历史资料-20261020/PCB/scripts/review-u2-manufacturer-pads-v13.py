exec(open('PCB/scripts/audit-u2-pin-boundary-v13.py',encoding='utf-8-sig').read().split('rows=[]')[0])
physical=[]
for lead in leads:
 g=lead['geom'];p=min(padlist,key=lambda p:g.centroid.distance(p['geom'].centroid));raw=p['raw'];ctr=g.centroid;x,y=round(ctr.x,2),round(ctr.y,2);w,h=g.bounds[2]-g.bounds[0],g.bounds[3]-g.bounds[1]
 if raw['defaultPad']['width']*.0254>1.7:w,h=(1.3,.6) if w>h else (.6,1.3);group='outer_48'
 elif abs(raw['defaultPad']['width']*.0254-1.3)<.002:w=h=1.3;group='central_6'
 else:w,h=(1,.7) if w>h else (.7,1);group='inner_55'
 actual=box(x-w/2,y-h/2,x+w/2,y+h/2);maxout=max(Point(xx,yy).distance(p['geom']) for xx,yy in actual.exterior.coords);physical.append({'pin':p['number'],'group':group,'manufacturerNominalPhysicalBoundsMm':list(actual.bounds),'maxOutsideCurrentPadMm':maxout,'coveredWithin1um':maxout<=.001})
print('Physical pad coverage within1um',sum(r['coveredWithin1um'] for r in physical),len(physical),'max outside',max(r['maxOutsideCurrentPadMm'] for r in physical))
import hashlib
record={'source':'ML307R AT V1.0.1 by China Mobile IoT, Figures19/20, printed pages55/56','pdfUrl':'https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1189/M307R_Hardware_Datasheet.pdf','pdfSha256':hashlib.sha256(Path('PCB/references/ML307R-Hardware-AT-V1.0.1.pdf').read_bytes()).hexdigest(),'scope':'Nominal dimensions read visually; no tolerance stack or assembly certification. Physical nominal shapes reconstructed on the documented nominal grid; this is not a substitute for manufacturer CAD.','physicalPadCoverageWithin1umCount':sum(r['coveredWithin1um'] for r in physical),'physicalPads':physical,'currentOuterLandMm':[1.8,.7],'recommendedOuterLandMm':[2.6,.6],'currentExternalToeNominalMm':.5,'recommendedExternalToeNominalMm':1.3,'currentModelOuterWidthMm':.75,'manufacturerPhysicalOuterWidthMm':.6,'currentModelCentralSquareMm':1.4,'manufacturerPhysicalCentralSquareMm':1.3,'PCBModified':False,'factoryDfmPassed':False,'trialRecommendedPadEnlargement':'Offline only; 44 auxiliary clearance pairs including2 old rounding pairs; includes RF feed, USB resistors, adjacent tracks. Pad substitution needs local relayout.'}
Path('PCB/manifests/u2-ml307-physical-reference-review-v13.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
