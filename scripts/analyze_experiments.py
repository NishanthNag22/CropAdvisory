"""Analyze measured runs and independently entered reviewer scores."""
import argparse
import csv
import itertools
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from crop_advisory.statistics import wilson, paired_bootstrap, cohen_kappa
from scripts.benchmark import summarize

KEYS=('model','language','prompt_style','strategy','reviewer')


def load_reviews(path):
    if path is None:return []
    rows=[];seen=set()
    with open(path,encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            if not row.get('reviewer','').strip():continue
            for field in ('correct','critical_error','complete'):
                value=row.get(field,'')
                if value not in ('','0','1'):raise ValueError(f'{field} must be blank, 0 or 1.')
                row[field]=None if value=='' else int(value)
            for field in ('agronomic_correctness_1_to_5','usefulness_1_to_5','translation_fidelity_1_to_5'):
                value=row.get(field,'')
                if value!='' and (not value.isdigit() or not 1<=int(value)<=5):raise ValueError(f'{field} must be blank or an integer 1–5.')
                row[field]=None if value=='' else int(value)
            key=tuple(row.get(k,'') for k in (*KEYS,'case','repeat'))
            if key in seen:raise ValueError('Duplicate reviewer rating for the same output.')
            seen.add(key);rows.append(row)
    return rows


def human_summary(reviews):
    groups=defaultdict(list)
    for r in reviews:groups[tuple(r.get(k,'') for k in KEYS)].append(r)
    summary=[]
    for key,rows in groups.items():
        result=dict(zip(KEYS,key));result['reviewed_outputs']=len(rows)
        for metric in ('correct','critical_error','complete'):
            grouped=defaultdict(list)
            for r in rows:
                if r[metric] is not None:grouped[r['case']].append(r[metric])
            # Independent unit is the case; repeated outputs are clustered.
            values=[any(v) if metric=='critical_error' else all(v) for v in grouped.values()]
            result[metric]={'numerator':sum(values),'denominator':len(values),'rate':sum(values)/len(values) if values else None,'ci95':wilson(sum(values),len(values)),
                'aggregation':'any reviewed repeat has error' if metric=='critical_error' else 'all reviewed repeats satisfy criterion'}
        for metric in ('agronomic_correctness_1_to_5','usefulness_1_to_5','translation_fidelity_1_to_5'):
            values=[r[metric] for r in rows if r[metric] is not None]
            result[metric]=statistics.mean(values) if values else None
        summary.append(result)
    return summary


def agreement(reviews):
    results=[]
    context=('case','model','language','prompt_style','strategy','repeat')
    for metric in ('correct','translation_fidelity_1_to_5'):
        indexed=defaultdict(dict)
        for r in reviews:
            if r.get(metric) is not None:indexed[r['reviewer']][tuple(r.get(k,'') for k in context)]=r[metric]
        for a,b in itertools.combinations(sorted(indexed),2):
            keys=sorted(set(indexed[a])&set(indexed[b]))
            if keys:results.append({'reviewers':[a,b],'metric':metric,'shared_outputs':len(keys),
                'unweighted_cohen_kappa':cohen_kappa([indexed[a][k] for k in keys],[indexed[b][k] for k in keys])})
    return results


def paired_latency(rows,a,b):
    groups=defaultdict(lambda:defaultdict(list))
    for r in rows:
        if r['status'] not in ('ok','abstained') or r['model'] not in (a,b):continue
        condition=(r['language'],r['prompt_style'],r.get('strategy','translate'))
        groups[condition][(r['model'],r['case'])].append(r['wall_seconds'])
    output=[]
    for condition,data in groups.items():
        common=sorted({case for model,case in data if model==a}&{case for model,case in data if model==b})
        if common:
            output.append({'models':[a,b],'condition':condition,'metric':'wall_seconds',**paired_bootstrap([statistics.mean(data[a,c]) for c in common],[statistics.mean(data[b,c]) for c in common])})
    return output


def paired_correctness(reviews,a,b):
    groups=defaultdict(lambda:defaultdict(list))
    for r in reviews:
        if r['model'] in (a,b) and r['correct'] is not None:
            condition=(r.get('language',''),r.get('prompt_style',''),r.get('strategy',''),r['reviewer'])
            groups[condition][(r['model'],r['case'])].append(r['correct'])
    results=[]
    for condition,data in groups.items():
        common=sorted({c for m,c in data if m==a}&{c for m,c in data if m==b})
        if common:results.append({'models':[a,b],'condition':condition,'metric':'reviewer_mean_correctness_per_case',**paired_bootstrap([statistics.mean(data[a,c]) for c in common],[statistics.mean(data[b,c]) for c in common])})
    return results


def plot_tradeoffs(summaries,human,path):
    # Quality/resource curves only use actual human-scored configurations.
    points=[]
    for row in summaries:
        matches=[r for r in human if all(r.get(k)==row.get(k) for k in ('model','language','prompt_style','strategy')) and r['correct']['rate'] is not None]
        if matches:
            points.append((row,statistics.mean(r['correct']['rate'] for r in matches)))
    if not points:return {'status':'not_generated','reason':'No human correctness ratings; no quality curve can be justified.'}
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:return {'status':'not_generated','reason':'Install requirements-analysis.txt to plot measured human scores.'}
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for row,quality in points:
        label=f"{row['model']} / {row['language']} / {row['prompt_style']} / {row['strategy']}"
        axes[0].scatter(row['median_wall_seconds'],quality,label=label)
        memory=row.get('max_sampled_process_tree_rss_bytes')
        if memory is not None:axes[1].scatter(memory/1024**3,quality,label=label)
    axes[0].set_xlabel('Median end-to-end latency (s)');axes[1].set_xlabel('Sampled process-tree RSS peak (GiB)')
    for ax in axes:ax.set_ylabel('Human-reviewed case correctness');ax.set_ylim(0,1.05);ax.grid(alpha=.2)
    axes[0].legend(fontsize=6);fig.tight_layout();fig.savefig(path,dpi=180);plt.close(fig)
    return {'status':'generated','path':str(path),'note':'Human-rated means across reviewers; RSS includes only monitored process trees.'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('results',type=Path)
    p.add_argument('--reviews',type=Path)
    p.add_argument('--compare-models',nargs=2)
    p.add_argument('--output',type=Path,default=Path('reports/analysis'))
    args=p.parse_args()
    try:
        raw=json.loads(args.results.read_text(encoding='utf-8'));rows=raw['rows'];reviews=load_reviews(args.reviews)
        summary=summarize(rows);human=human_summary(reviews)
        report={'measured_summary':summary,'human_summary':human,'inter_rater_agreement':agreement(reviews),
            'paired_latency':paired_latency(rows,*args.compare_models) if args.compare_models else [],
            'paired_correctness':paired_correctness(reviews,*args.compare_models) if args.compare_models else [],
            'note':'No reviewer scores are synthesized. Confidence intervals are conditional on this authored case sample, not general field accuracy.'}
        args.output.mkdir(parents=True,exist_ok=True)
        report['plot']=plot_tradeoffs(summary,human,args.output/'quality_resource.png')
        (args.output/'analysis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        with (args.output/'summary.csv').open('w',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(summary[0]) if summary else ['model']);writer.writeheader();writer.writerows(summary)
    except (OSError,ValueError,KeyError) as exc:p.error(str(exc))
    print('Saved analysis to',args.output)
    return 0

if __name__=='__main__':raise SystemExit(main())
