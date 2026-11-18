"""Reproducible local evaluation; real LLM timings only when a model is available."""
import argparse
import csv
import itertools
import json
import platform
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from crop_advisory.engine import ROOT, Ollama, AdvisoryError, advise, validate_input
from crop_advisory.retrieval import retrieve


def retrieval_score(case, evidence):
    expected=set(case['expected_topics']);actual={e['topic'] for e in evidence}
    return {'expected_topics':sorted(expected),'retrieved_topics':sorted(actual),
            'all_expected_retrieved':expected.issubset(actual) if expected else not actual,
            'crop_isolation':all(e['crop']==case['crop'] for e in evidence)}


def run(cases,models,languages,styles,repeats,client=None):
    client=client or Ollama()
    rows=[]
    for model,language,style,repeat,case in itertools.product(models,languages,styles,range(repeats),cases):
        payload=dict(case,language=language,prompt_style=style)
        row={'case':case['id'],'crop':case['crop'],'model':model,'language':language,'prompt_style':style,'repeat':repeat,
             'status':'pending','error':None}
        started=time.perf_counter()
        try:
            result=advise(payload,client=client,model=model,mode='evidence' if model=='evidence-only' else 'llm')
            row.update(status='abstained' if model!='evidence-only' and not result['generation_performed'] else 'ok',result=result,**retrieval_score(case,result['evidence']))
            metrics=result['metrics'];duration=metrics.get('eval_duration') or 0
            row['generation_tokens_per_second']=(metrics.get('eval_count') or 0)/(duration/1e9) if duration else None
            if model!='evidence-only' and result['generation_performed']:
                try:
                    loaded=client.request('/api/ps').get('models',[])
                    match=next((m for m in loaded if m.get('name')==model or m.get('model')==model or m.get('name')==model+':latest'),None)
                    row['loaded_model']=match
                except AdvisoryError:
                    row['loaded_model']=None
        except (ValueError,AdvisoryError) as exc:
            row.update(status='error',error=str(exc))
        row['wall_seconds']=round(time.perf_counter()-started,4)
        rows.append(row)
    return rows


def summarize(rows):
    groups=defaultdict(list)
    for row in rows:
        groups[(row['model'],row['language'],row['prompt_style'])].append(row)
    summary=[]
    for key,group in groups.items():
        good=[r for r in group if r['status'] in ('ok','abstained')]
        rates=[r['generation_tokens_per_second'] for r in good if r['generation_tokens_per_second'] is not None]
        outputs=defaultdict(list)
        for r in good:
            outputs[r['case']].append(r['result']['translation'] or r['result']['answer'])
        repeated=[len(set(texts))==1 for texts in outputs.values() if len(texts)>1]
        summary.append(dict(model=key[0],language=key[1],prompt_style=key[2],attempts=len(group),successes=len(good),
            failures=len(group)-len(good),abstentions=sum(r['status']=='abstained' for r in group),generated_advisories=sum(r['result']['generation_performed'] for r in good),mean_wall_seconds=statistics.mean(r['wall_seconds'] for r in good) if good else None,
            mean_generation_tokens_per_second=statistics.mean(rates) if rates else None,
            retrieval_all_expected_rate=sum(r['all_expected_retrieved'] for r in good)/len(good) if good else None,
            repeat_exact_consistency=sum(repeated)/len(repeated) if repeated else None))
    return summary


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--models',nargs='+',default=['evidence-only'])
    p.add_argument('--languages',nargs='+',default=['en'])
    p.add_argument('--styles',nargs='+',choices=['concise','structured'],default=['concise','structured'])
    p.add_argument('--repeats',type=int,default=1)
    p.add_argument('--cases',type=Path,default=ROOT/'data/pipeline_cases.json')
    p.add_argument('--output',type=Path,default=ROOT/'reports/benchmark')
    args=p.parse_args()
    if args.repeats<1:p.error('--repeats must be positive')
    cases=json.loads(args.cases.read_text(encoding='utf-8'))
    if not cases:p.error('Cases must not be empty')
    args.output.mkdir(parents=True,exist_ok=True)
    client=Ollama()
    metadata={'created_at':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'python':platform.python_version(),
              'note':'Automated retrieval, support and translation checks are proxies, not validated agronomic accuracy. Loaded model size is not peak process RAM.'}
    try:
        metadata['installed_models']=client.request('/api/tags') if args.models!=['evidence-only'] else None
    except AdvisoryError as exc:
        metadata['model_metadata_error']=str(exc)
    rows=run(cases,args.models,args.languages,args.styles,args.repeats,client)
    (args.output/'results.json').write_text(json.dumps({'metadata':metadata,'summary':summarize(rows),'rows':rows},ensure_ascii=False,indent=2),encoding='utf-8')
    fields=['case','crop','model','language','prompt_style','repeat','status','error','wall_seconds','generation_tokens_per_second','all_expected_retrieved','crop_isolation']
    with (args.output/'measurements.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    with (args.output/'human_review.csv').open('w',encoding='utf-8-sig',newline='') as f:
        fields=['case','model','language','prompt_style','repeat','english','translation','agronomic_correctness_1_to_5','usefulness_1_to_5','translation_fidelity_1_to_5','negations_preserved','reviewer','notes']
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for row in rows:
            result=row.get('result',{})
            writer.writerow({**{k:row[k] for k in ['case','model','language','prompt_style','repeat']},'english':result.get('answer',''),'translation':result.get('translation','')})
    print(json.dumps(summarize(rows),indent=2))
    print('Saved results, measurements, and blank human-review fields to',args.output)
    return int(any(row['status']=='error' for row in rows))

if __name__=='__main__':
    raise SystemExit(main())
