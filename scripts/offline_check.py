"""Record a loopback-only client run and optional host-adapter precondition."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from crop_advisory.offline import loopback_only, active_network_interfaces
from crop_advisory.engine import advise, AdvisoryError


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--mode',choices=['llm','evidence'],default='evidence')
    p.add_argument('--model',default=None)
    p.add_argument('--require-network-disconnected',action='store_true')
    p.add_argument('--output',type=Path,default=Path('reports/offline-check.json'))
    args=p.parse_args()
    interfaces=active_network_interfaces()
    report={'created_at':datetime.now(timezone.utc).isoformat(),'active_nonloopback_interfaces':interfaces,
        'client_network_guard':'loopback-only TCP and DNS','network_isolation_verified':False,
        'limitation':'The guard does not sandbox Ollama. For a genuine offline hardware demonstration disconnect host networking and run both processes locally.',
        'mode':args.mode,'model':args.model,'status':'pending'}
    if args.require_network_disconnected and interfaces!=[]:
        report.update(status='precondition_failed',error='Non-loopback interfaces are active or could not be inspected. Disconnect host networking before this run.')
    else:
        try:
            with loopback_only():report['result']=advise({'crop':'tomato','question':'What should guide irrigation?'},model=args.model,mode=args.mode)
            report['status']='completed'
        except (ValueError,AdvisoryError,PermissionError) as exc:report.update(status='error',error=str(exc))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='result'},indent=2))
    return int(report['status']!='completed')

if __name__=='__main__':raise SystemExit(main())
