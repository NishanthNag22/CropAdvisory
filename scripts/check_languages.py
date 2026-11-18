"""Run the actual local pipeline in selected languages; no synthetic quality scores."""
import argparse
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from crop_advisory.engine import advise, Ollama, AdvisoryError, LANGUAGES


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',default='llama3.2:3b')
    parser.add_argument('--languages',nargs='+',choices=['hi','kn','ta','te'],default=['hi','kn','ta','te'])
    parser.add_argument('--output',type=Path,default=Path('reports/language-check.json'))
    args=parser.parse_args()
    payload={'crop':'tomato','moisture':28,'temperature':30,'ph':6.8,'region':'Tamil Nadu, India',
        'soil_type':'Loam','growth_stage':'Flowering','prompt_style':'concise',
        'question':'Give two short checks before changing tomato irrigation.'}
    rows=[];client=Ollama()
    for language in args.languages:
        print(f'Testing {LANGUAGES[language]} with the local model...',flush=True)
        started=time.perf_counter()
        row={'language':language,'model':args.model}
        try:
            result=advise(dict(payload,language=language),client=client,model=args.model)
            passed=result['translation_status']=='model_assessed' and bool(result['translation'])
            row.update(automated_checks_passed=passed,result=result)
            print(f"{LANGUAGES[language]}: {result['translation_status']}"+(f" - {result['translation_failure_reason']}" if result['translation_failure_reason'] else ''),flush=True)
        except (ValueError,AdvisoryError) as exc:
            row.update(automated_checks_passed=False,error=str(exc));print(str(exc),flush=True)
        row['wall_seconds']=round(time.perf_counter()-started,3);rows.append(row)
        # Save completed languages immediately so a later interruption loses no results.
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps({'note':'Actual local-model runs. Passing automated checks is not proof of translation fidelity; fluent-speaker review remains required.','rows':rows},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Saved local results to',args.output)
    return int(any(not row['automated_checks_passed'] for row in rows))

if __name__=='__main__':raise SystemExit(main())
