"""Guarded bridge runner for V0.12. Never replay historical mutation scripts."""
import argparse, json, urllib.request, urllib.error, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def request(path, payload=None, timeout=60):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request('http://127.0.0.1:49620'+path, data=data,
                                 headers={'Content-Type':'application/json; charset=utf-8'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail=exc.read().decode('utf-8',errors='replace')
        raise RuntimeError('Bridge HTTP '+str(exc.code)+': '+detail) from exc

def run(code, report=None, timeout=60):
    health=request('/health', timeout=3)
    if health.get('service')!='easyeda-bridge' or not health.get('edaConnected') or health.get('edaWindowCount')!=1:
        raise RuntimeError('Expected one connected EasyEDA window')
    if health.get('pendingRequests'):
        raise RuntimeError('Previous EDA request is still pending; inspect before continuing')
    result=request('/execute', {'code':code,'windowId':health['activeWindowId']}, timeout)
    if report:
        dest=ROOT/report; dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    if not result.get('success'):
        raise RuntimeError(json.dumps(result,ensure_ascii=False))
    return result.get('result')

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('script'); parser.add_argument('--report'); parser.add_argument('--timeout',type=int,default=60)
    args=parser.parse_args()
    result=run(Path(args.script).read_text(encoding='utf-8-sig'),args.report,args.timeout)
    if isinstance(result,dict) and 'bytes' in result:
        filename=result.get('name','export-v12.bin'); dest=ROOT/'eda'/filename
        dest.write_bytes(bytes(result.pop('bytes')));result['savedTo']=str(dest)
    if isinstance(result,dict) and ('content' in result or 'source' in result):
        print(json.dumps({k:len(v) if k in ['content','source'] and isinstance(v,str) else v for k,v in result.items() if k not in ['layers','stack']},ensure_ascii=True)); raise SystemExit(0)
    output=json.dumps(result,ensure_ascii=True)
    print(output if len(output)<4500 else output[:4500]+' [full output saved to report]')
