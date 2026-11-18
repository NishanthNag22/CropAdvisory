import json
import socket
from unittest.mock import Mock
import pytest
from crop_advisory.engine import validate_input, build_messages, ROOT
from crop_advisory.statistics import percentile, wilson, paired_bootstrap, cohen_kappa
from crop_advisory.resources import energy_delta, ResourceMonitor
from crop_advisory.offline import loopback_only
from crop_advisory.research_pipeline import direct_advice
from scripts.benchmark import load_dataset, run, summarize
from scripts.analyze_experiments import human_summary, load_reviews, paired_correctness


def test_true_unstructured_baseline_same_evidence_and_readings():
    a=validate_input({'moisture':32,'ph':6.8,'question':'irrigation','prompt_style':'structured'})
    b=dict(a,prompt_style='unstructured')
    structured=build_messages(a,[]);plain=build_messages(b,[])
    json.loads(structured[1]['content'])
    with pytest.raises(ValueError):json.loads(plain[1]['content'])
    assert structured[0]==plain[0]
    assert '32' in plain[1]['content'] and '6.8' in plain[1]['content']


def test_statistics_known_values():
    assert percentile([1,2,3,4,5],.5)==3
    lo,hi=wilson(5,10)
    assert .23<lo<.24 and .76<hi<.77
    paired=paired_bootstrap([2,3,4],[1,2,3],repetitions=100)
    assert paired['ci95']==[1,1] and paired['mean_paired_difference']==1
    assert cohen_kappa([0,1,0,1],[0,1,0,1])==1


def test_energy_wraparound():
    assert energy_delta({'a':{'energy_uj':95,'range_uj':100}},{'a':{'energy_uj':5,'range_uj':100}})==.00001
    assert energy_delta({}, {}) is None


def test_resource_monitor_reports_scope_even_without_hardware():
    with ResourceMonitor() as monitor:sum(range(100))
    report=monitor.report()
    assert report['monitor_pids'] and 'scope' in report


def test_offline_guard_blocks_external_dns_without_contacting_it():
    with loopback_only():
        with pytest.raises(PermissionError):socket.getaddrinfo('example.com',443)
    assert socket.getaddrinfo('127.0.0.1',80)


def test_dataset_splits_and_review_provenance():
    development,meta=load_dataset(ROOT/'data/research_cases.json','development')
    evaluation,_=load_dataset(ROOT/'data/research_cases.json','evaluation')
    assert not {c['id'] for c in development}&{c['id'] for c in evaluation}
    assert not meta['expert_reviewed'] and all(not c['expert_reviewed'] for c in evaluation)


def test_research_cases_retrieve_expected_topics_or_abstain():
    cases,_=load_dataset(ROOT/'data/research_cases.json')
    rows=run(cases,['evidence-only'],['en'],['structured'],1)
    assert all(r['status']=='ok' for r in rows)
    assert all(r['all_expected_retrieved'] for r in rows)
    assert summarize(rows)[0]['p95_wall_seconds'] is not None


def test_direct_generation_arm_is_named_and_screened():
    client=Mock();client.chat.side_effect=[('सिंचाई की जाँच करें।',{}),(json.dumps({'assessments':[{'id':0,'status':'supported','evidence':[1],'reason':'fixture'}]}),{})]
    result=direct_advice({'question':'irrigation','language':'hi'},client,'test')
    assert result['mode']=='research_direct' and result['translation']
    assert 'Answer directly in Hindi.' in client.chat.call_args_list[0].args[1][0]['content']
    assert result['human_review_required']


def test_missing_reviews_never_become_human_accuracy():
    assert human_summary([])==[]
    assert load_reviews(None)==[]


def test_unlabelled_review_scores_are_ignored(tmp_path):
    path=tmp_path/'reviews.csv';path.write_text('case,reviewer,correct\na,,1\n')
    assert load_reviews(path)==[]


def test_reviewed_repetitions_are_clustered_by_case():
    rows=[dict(model='a',language='en',prompt_style='structured',strategy='translate',reviewer='expert',case='x',correct=i,critical_error=0,complete=1,agronomic_correctness_1_to_5=None,usefulness_1_to_5=None,translation_fidelity_1_to_5=None) for i in (1,0)]
    result=human_summary(rows)[0]
    assert result['correct']['denominator']==1 and result['correct']['numerator']==0

def test_interface_probe_handles_os_restrictions(monkeypatch):
    import psutil
    from crop_advisory.offline import active_network_interfaces
    def denied():raise PermissionError('restricted')
    monkeypatch.setattr(psutil,'net_if_addrs',denied)
    assert active_network_interfaces() is None


def test_invalid_or_fake_expert_ratings_rejected(tmp_path):
    path=tmp_path/'reviews.csv';path.write_text('case,reviewer,correct\na,expert,2\n')
    with pytest.raises(ValueError):load_reviews(path)
