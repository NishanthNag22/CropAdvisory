import io
import json
from unittest.mock import Mock
from crop_advisory.sensors import read_csv
from scripts.benchmark import run, summarize

def test_csv_keeps_zero_and_missing_values():
    rows=list(read_csv(io.StringIO('crop,moisture,temperature,ph,question\ntomato,0,,6.8,irrigation\n')))
    assert rows[0]['input']['moisture']==0
    assert rows[0]['input']['temperature'] is None

def test_csv_bad_row_does_not_hide_good_row():
    rows=list(read_csv(io.StringIO('crop,moisture,temperature,ph,question\nrice,101,25,,water\nwheat,30,26,,water\n')))
    assert rows[0]['error'] and rows[1]['input']['crop']=='wheat'

def test_benchmark_errors_are_failures_not_zero_scores():
    case={'id':'test','crop':'tomato','question':'irrigation','expected_topics':['soil_moisture']}
    from crop_advisory.engine import AdvisoryError
    client=Mock();client.chat.side_effect=AdvisoryError('No model')
    rows=run([case],['test-model'],['en'],['concise'],1,client)
    summary=summarize(rows)[0]
    assert summary['failures']==1 and summary['mean_wall_seconds'] is None

def test_offline_cases_are_crop_isolated():
    from crop_advisory.engine import ROOT
    cases=json.loads((ROOT/'data/pipeline_cases.json').read_text())
    rows=run(cases,['evidence-only'],['en'],['structured'],2)
    assert all(r['status']=='ok' and r['crop_isolation'] and r['all_expected_retrieved'] for r in rows)
    assert summarize(rows)[0]['repeat_exact_consistency']==1

def test_benchmark_abstention_is_not_model_generation():
    case={'id':'outside','crop':'rice','question':'What pH is ideal?','expected_topics':[]}
    client=Mock()
    rows=run([case],['not-installed'],['en'],['concise'],1,client)
    summary=summarize(rows)[0]
    assert summary['abstentions']==1 and summary['generated_advisories']==0
    client.chat.assert_not_called()
