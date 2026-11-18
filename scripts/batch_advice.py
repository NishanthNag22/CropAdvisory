"""Process CSV logs, preserving failures per row instead of inventing readings."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from crop_advisory.sensors import read_csv
from crop_advisory.engine import advise, AdvisoryError


def main():
    p=argparse.ArgumentParser()
    p.add_argument('csv_file',type=Path)
    p.add_argument('--mode',choices=['llm','evidence'],default='llm')
    p.add_argument('--model',default=None)
    p.add_argument('--output',type=Path,default=Path('reports/batch.jsonl'))
    args=p.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    failures=0
    try:
        with args.csv_file.open(encoding='utf-8-sig',newline='') as stream, args.output.open('w',encoding='utf-8') as out:
            for row in read_csv(stream):
                if not row['error']:
                    try:
                        row['result']=advise(row['raw_input'],mode=args.mode,model=args.model)
                    except (ValueError,AdvisoryError) as exc:
                        row['error']=str(exc)
                failures+=int(bool(row['error']))
                out.write(json.dumps(row,ensure_ascii=False)+'\n')
    except (OSError,ValueError) as exc:
        print(str(exc),file=sys.stderr);return 1
    print(f'Results: {args.output}; failed rows: {failures}')
    return int(failures>0)

if __name__=='__main__':
    raise SystemExit(main())
