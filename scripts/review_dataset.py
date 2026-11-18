"""Export blank case-review forms and import completed human annotations.

This validates provenance completeness; it cannot verify a reviewer's credentials.
"""
import argparse
import copy
import csv
import hashlib
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from crop_advisory.retrieval import load_entries

FIELDS=['id','split','crop','question','input_json','rubric_json','source_urls_json','reviewer','reviewed_on','reference_answer','review_decision','notes']


def export_reviews(dataset,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader()
        for case in dataset['cases']:
            writer.writerow({'id':case['id'],'split':case.get('split',''),'crop':case['crop'],'question':case.get('question',''),
                'input_json':json.dumps(case,ensure_ascii=False),'rubric_json':json.dumps(case.get('rubric',{}),ensure_ascii=False),
                'source_urls_json':json.dumps(sorted({e['source_url'] for e in load_entries(case['crop'])})),
                'reviewer':'','reviewed_on':'','reference_answer':'','review_decision':'','notes':''})


def import_reviews(dataset,path,today=None):
    today=today or datetime.now(timezone.utc).date()
    result=copy.deepcopy(dataset);cases={c['id']:c for c in result['cases']};seen=set()
    with open(path,encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            identifier=row.get('id')
            if identifier not in cases or identifier in seen:raise ValueError('Unknown or duplicate case review id.')
            seen.add(identifier)
            decision=row.get('review_decision','').strip()
            if not decision:continue
            if decision not in ('approved','needs_revision'):raise ValueError('review_decision must be approved or needs_revision.')
            reviewer=row.get('reviewer','').strip();reviewed=row.get('reviewed_on','').strip()
            if not reviewer or not reviewed:raise ValueError('A decision requires reviewer identity and review date.')
            reviewed_date=date.fromisoformat(reviewed)
            if reviewed_date>today:raise ValueError('Review date cannot be in the future.')
            rubric=json.loads(row.get('rubric_json') or '{}')
            urls=json.loads(row.get('source_urls_json') or '[]')
            if not isinstance(rubric,dict) or not isinstance(urls,list) or any(not isinstance(u,str) or urlparse(u).scheme not in ('http','https') for u in urls):raise ValueError('Invalid rubric or source URLs.')
            reference=row.get('reference_answer','').strip()
            if decision=='approved' and (not reference or not urls or not rubric.get('required_points')):
                raise ValueError('Approval requires a reference answer, required-point rubric and sources.')
            case=cases[identifier];case['expert_reviewed']=decision=='approved'
            case['expert_review']={'reviewer':reviewer,'reviewed_on':reviewed,'decision':decision,'source_urls':urls,'notes':row.get('notes','')}
            case['rubric']=dict(rubric,reference_answer=reference or None)
    result['expert_reviewed']=all(c.get('expert_reviewed',False) for c in result['cases'])
    result['review_status']='All cases have supplied human review metadata.' if result['expert_reviewed'] else 'Review incomplete; inspect each case.'
    result['annotation_sha256']=hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('action',choices=['export','import'])
    p.add_argument('dataset',type=Path)
    p.add_argument('--annotations',type=Path)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    try:
        data=json.loads(args.dataset.read_text(encoding='utf-8'))
        if args.action=='export':export_reviews(data,args.output)
        else:
            if args.annotations is None:p.error('--annotations is required for import')
            updated=import_reviews(data,args.annotations)
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps(updated,ensure_ascii=False,indent=2),encoding='utf-8')
    except (OSError,ValueError,KeyError) as exc:p.error(str(exc))
    print('Saved',args.output)

if __name__=='__main__':main()
