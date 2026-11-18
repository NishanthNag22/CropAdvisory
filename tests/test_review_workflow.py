import csv
import json
from datetime import date
import pytest
from scripts.review_dataset import export_reviews, import_reviews, FIELDS
from scripts.analyze_experiments import agreement

CASE={'id':'fixture','crop':'tomato','question':'irrigation','split':'evaluation','expert_reviewed':False,'rubric':{'required_points':['check drainage'],'reference_answer':None}}


def test_review_export_does_not_invent_human_labels(tmp_path):
    path=tmp_path/'blank.csv';export_reviews({'cases':[CASE]},path)
    rows=list(csv.DictReader(path.open(encoding='utf-8-sig')))
    assert rows[0]['reviewer']=='' and rows[0]['reference_answer']=='' and rows[0]['review_decision']==''
    assert not import_reviews({'cases':[CASE]},path)['expert_reviewed']


def write_review(path,**changes):
    row={'id':'fixture','reviewer':'test-fixture-reviewer','reviewed_on':'2026-11-18','review_decision':'approved','reference_answer':'Test fixture reference, not expert evidence.','rubric_json':json.dumps({'required_points':['check drainage']}),'source_urls_json':'["https://example.com/test-fixture"]',**changes}
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader();writer.writerow(row)


def test_approval_requires_reference_and_sources(tmp_path):
    path=tmp_path/'ratings.csv';write_review(path,reference_answer='')
    with pytest.raises(ValueError):import_reviews({'cases':[CASE]},path,date(2026,11,18))


def test_import_preserves_review_provenance_without_mutating_original(tmp_path):
    path=tmp_path/'ratings.csv';write_review(path)
    original={'cases':[CASE]}
    reviewed=import_reviews(original,path,date(2026,11,18))
    assert reviewed['expert_reviewed'] and reviewed['cases'][0]['expert_review']['reviewer']=='test-fixture-reviewer'
    assert not original['cases'][0]['expert_reviewed']


def test_inter_rater_fidelity_agreement_is_separate():
    rows=[]
    for reviewer in ['fixture-a','fixture-b']:
        for i in (1,2):rows.append({'case':str(i),'reviewer':reviewer,'correct':i-1,'translation_fidelity_1_to_5':i})
    result=agreement(rows)
    assert {r['metric'] for r in result}=={'correct','translation_fidelity_1_to_5'}
    assert all(r['unweighted_cohen_kappa']==1 for r in result)
