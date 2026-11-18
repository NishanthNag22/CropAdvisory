"""Versioned local experiments; absent human ratings and hardware data stay absent."""
import argparse
import csv
import hashlib
import importlib.metadata
import itertools
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from crop_advisory.engine import ROOT, Ollama, AdvisoryError, advise, build_messages, LANGUAGES
from crop_advisory.research_pipeline import direct_advice
from crop_advisory.resources import ResourceMonitor
from crop_advisory.statistics import percentile, wilson


def retrieval_score(case,evidence):
    expected=set(case['expected_topics']);actual={e['topic'] for e in evidence}
    return {'expected_topics':sorted(expected),'retrieved_topics':sorted(actual),
        'all_expected_retrieved':expected.issubset(actual) if expected else not actual,
        'crop_isolation':all(e['crop']==case['crop'] for e in evidence)}


def load_dataset(path,split='all'):
    raw=json.loads(Path(path).read_text(encoding='utf-8'))
    cases=raw.get('cases',[]) if isinstance(raw,dict) else raw
    metadata={k:v for k,v in raw.items() if k!='cases'} if isinstance(raw,dict) else {'version':'legacy-list','expert_reviewed':False}
    if not isinstance(cases,list) or not cases:raise ValueError('Dataset must contain cases.')
    ids=set()
    for case in cases:
        if not case.get('id') or case['id'] in ids:raise ValueError('Case identifiers must be present and unique.')
        ids.add(case['id'])
        if not isinstance(case.get('expected_topics'),list):raise ValueError('Each case needs expected_topics.')
        if case.get('expert_reviewed') and not case.get('expert_review',{}).get('reviewer'):
            raise ValueError('Expert-reviewed claims require a named reviewer.')
    chosen=[c for c in cases if split=='all' or c.get('split')==split]
    if not chosen:raise ValueError('No cases in the requested split.')
    return chosen,dict(metadata,selected_split=split,dataset_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest())


def run(cases,models,languages,styles,repeats,client=None,strategies=None,monitor_pids=None):
    client=client or Ollama();rows=[]
    for model,language,style,strategy,repeat,case in itertools.product(models,languages,styles,strategies or ['translate'],range(repeats),cases):
        payload=dict(case,language=language,prompt_style=style)
        row={'case':case['id'],'crop':case['crop'],'split':case.get('split','unspecified'),
            'model':model,'language':language,'prompt_style':style,'strategy':strategy,'repeat':repeat,
            'status':'pending','error':None,'expert_reviewed_case':case.get('expert_reviewed',False),
            'inference_settings':{'temperature':0,'seed':42,'num_ctx':4096,'num_predict':800}}
        started=time.perf_counter()
        monitor=ResourceMonitor(monitor_pids)
        try:
            if model=='evidence-only' and strategy=='direct':raise ValueError('Direct generation requires a local model.')
            with monitor:
                result=direct_advice(payload,client,model) if strategy=='direct' else advise(payload,client=client,model=model,mode='evidence' if model=='evidence-only' else 'llm')
            abstained=model!='evidence-only' and (not result['generation_performed'] or result.get('advisory_withheld',False))
            row.update(status='abstained' if abstained else 'ok',result=result,**retrieval_score(case,result['evidence']))
            row['resources']=monitor.report()
            messages=build_messages(result['input'],result['evidence'])
            if strategy=='direct':messages[0]['content']=messages[0]['content'].replace('Answer in English.',f"Answer directly in {LANGUAGES[language]}.")
            row['generation_messages']=messages
            metrics=result['metrics'];duration=metrics.get('eval_duration') or 0
            row['generation_tokens_per_second']=(metrics.get('eval_count') or 0)/(duration/1e9) if duration else None
            if model!='evidence-only' and result['generation_performed']:
                try:
                    loaded=client.request('/api/ps').get('models',[])
                    row['loaded_model']=next((m for m in loaded if m.get('name') in (model,model+':latest') or m.get('model')==model),None)
                except AdvisoryError:row['loaded_model']=None
        except (ValueError,AdvisoryError) as exc:
            row.update(status='error',error=str(exc))
            if hasattr(monitor,'after'):row['resources']=monitor.report()
        row['wall_seconds']=round(time.perf_counter()-started,6)
        rows.append(row)
    return rows


def summarize(rows):
    groups=defaultdict(list)
    for row in rows:groups[(row['model'],row['language'],row['prompt_style'],row.get('strategy','translate'))].append(row)
    summary=[]
    for key,group in groups.items():
        good=[r for r in group if r['status'] in ('ok','abstained')]
        rates=[r['generation_tokens_per_second'] for r in good if r['generation_tokens_per_second'] is not None]
        outputs=defaultdict(list)
        for r in good:outputs[r['case']].append(r['result']['translation'] or r['result']['answer'])
        repeated=[len(set(texts))==1 for texts in outputs.values() if len(texts)>1]
        latencies=[r['wall_seconds'] for r in good]
        hit=sum(r['all_expected_retrieved'] for r in good)
        peaks=[r.get('resources',{}).get('sampled_peak_process_tree_rss_bytes') for r in good]
        peaks=[p for p in peaks if p is not None]
        # Repetitions of the same case are not independent observations for CIs.
        case_hits=defaultdict(list)
        for r in good:case_hits[r['case']].append(r['all_expected_retrieved'])
        per_case=[all(v) for v in case_hits.values()]
        summary.append(dict(model=key[0],language=key[1],prompt_style=key[2],strategy=key[3],attempts=len(group),successes=len(good),
            failures=len(group)-len(good),abstentions=sum(r['status']=='abstained' for r in group),
            generated_advisories=sum(r['result']['generation_performed'] for r in good),
            mean_wall_seconds=statistics.mean(latencies) if latencies else None,
            median_wall_seconds=percentile(latencies,.5),p95_wall_seconds=percentile(latencies,.95),
            max_sampled_process_tree_rss_bytes=max(peaks) if peaks else None,
            mean_generation_tokens_per_second=statistics.mean(rates) if rates else None,
            retrieval_all_expected_numerator=hit,retrieval_all_expected_denominator=len(good),
            retrieval_all_expected_rate=hit/len(good) if good else None,
            retrieval_case_ci95=wilson(sum(per_case),len(per_case)),retrieval_unique_cases=len(per_case),
            repeat_exact_consistency=sum(repeated)/len(repeated) if repeated else None,
            note='Retrieval checks and repeated-text agreement are not agronomic correctness. Latencies include metadata collection.'))
    return summary


def manifest(args,dataset,client):
    dependencies={}
    for name in ('numpy','pytest','psutil','sentence-transformers','faiss-cpu'):
        try:dependencies[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:dependencies[name]=None
    files={}
    for p in sorted(list((ROOT/'crop_advisory').glob('*.py')) + list((ROOT/'data').glob('*.json'))):
        files[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    for spec in args.model_files:
        name,sep,path=spec.partition('=')
        if not sep:raise ValueError('--model-files entries must be alias=/path/to/model.gguf')
        digest=hashlib.sha256()
        with open(path,'rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
        files[name]={'path':path,'sha256':digest.hexdigest(),'bytes':os.path.getsize(path)}
    info={'created_at':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'cpu':platform.processor(),
        'machine':platform.machine(),'logical_cpus':os.cpu_count(),'python':platform.python_version(),'dependencies':dependencies,'files':files,'dataset':dataset,
        'arguments':{k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()},
        'network_isolation_verified':False,'note':'Expert ratings and hardware values are never inferred from software tests.'}
    try:
        info['git_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        info['git_dirty']=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip())
    except (OSError,subprocess.SubprocessError):info['git_commit']=None
    if args.models!=['evidence-only']:
        for path,key in [('/api/tags','installed_models'),('/api/version','ollama_version')]:
            try:info[key]=client.request(path)
            except AdvisoryError as exc:info[key]={'error':str(exc)}
    return info


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--models',nargs='+',default=['evidence-only'])
    p.add_argument('--languages',nargs='+',default=['en'])
    p.add_argument('--styles',nargs='+',choices=['concise','structured','unstructured'],default=['structured','unstructured'])
    p.add_argument('--strategies',nargs='+',choices=['translate','direct'],default=['translate'])
    p.add_argument('--repeats',type=int,default=1)
    p.add_argument('--warmup-runs',type=int,default=0)
    p.add_argument('--monitor-pids',nargs='*',type=int,default=[])
    p.add_argument('--model-files',nargs='*',default=[])
    p.add_argument('--cases',type=Path,default=ROOT/'data/research_cases.json')
    p.add_argument('--split',choices=['all','development','evaluation'],default='evaluation')
    p.add_argument('--output',type=Path,default=ROOT/'reports/benchmark')
    args=p.parse_args()
    if args.repeats<1 or args.warmup_runs<0:p.error('Repetitions must be positive; warm-ups must not be negative.')
    try:
        cases,dataset=load_dataset(args.cases,args.split)
        args.output.mkdir(parents=True,exist_ok=True);client=Ollama()
        metadata=manifest(args,dataset,client)
    except (OSError,ValueError) as exc:p.error(str(exc))
    metadata['warmups']=[]
    for model in args.models:
        if model!='evidence-only':
            for i in range(args.warmup_runs):
                attempt={'model':model,'iteration':i}
                try:advise(dict(cases[0],language='en'),client=client,model=model);attempt['status']='ok'
                except (ValueError,AdvisoryError) as exc:attempt.update(status='error',error=str(exc))
                metadata['warmups'].append(attempt)
    rows=run(cases,args.models,args.languages,args.styles,args.repeats,client,args.strategies,args.monitor_pids)
    (args.output/'results.json').write_text(json.dumps({'metadata':metadata,'summary':summarize(rows),'rows':rows},ensure_ascii=False,indent=2),encoding='utf-8')
    fields=['case','crop','split','model','language','prompt_style','strategy','repeat','status','error','wall_seconds','generation_tokens_per_second','all_expected_retrieved','crop_isolation']
    with (args.output/'measurements.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    with (args.output/'human_review.csv').open('w',encoding='utf-8-sig',newline='') as f:
        fields=['case','model','language','prompt_style','strategy','repeat','english','translation','correct','critical_error','complete','agronomic_correctness_1_to_5','usefulness_1_to_5','translation_fidelity_1_to_5','negations_preserved','reviewer','notes']
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for row in rows:
            result=row.get('result',{})
            writer.writerow({**{k:row[k] for k in ['case','model','language','prompt_style','strategy','repeat']},'english':result.get('answer',''),'translation':result.get('translation','')})
    print(json.dumps(summarize(rows),indent=2))
    print('Saved raw outputs, prompts, provenance, measurements and blank review fields to',args.output)
    return int(any(row['status']=='error' for row in rows))

if __name__=='__main__':raise SystemExit(main())
