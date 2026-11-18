import json
from unittest.mock import Mock
from crop_advisory.verification import rule_check, assess, screened_answer
from crop_advisory.engine import advise, AdvisoryError
import pytest
EVIDENCE=[{'topic':'soil_moisture','guidance':'Check actual soil moisture and drainage before changing irrigation.','crop':'tomato'}]

def test_paraphrase_requires_semantic_assessment():
    assert rule_check('Assess drainage and soil moisture before adjusting watering.',EVIDENCE)[0]=='unassessed'

def test_supported_paraphrase_cites_evidence():
    client=Mock();client.chat.return_value=(json.dumps({'assessments':[{'id':0,'status':'supported','evidence':[1],'reason':'same check'}]}),{})
    results,error=assess('Assess drainage and soil moisture before adjusting watering.',EVIDENCE,client,'test')
    assert error is None and results[0]['method']=='local_model'
    assert '[Evidence 1]' in screened_answer(results,EVIDENCE)

@pytest.mark.parametrize('claim,status',[
    ('Yellow leaves definitely confirm nitrogen deficiency.','contradicted'),
    ('Apply 50 kg/ha urea.','insufficient_evidence'),
    ('Spray fungicide.','insufficient_evidence'),
    ('Irrigate now.','insufficient_evidence')])
def test_unsafe_claims_do_not_reach_reviewer(claim,status):
    client=Mock()
    checks,error=assess(claim,EVIDENCE,client,'test')
    assert checks[0]['status']==status
    client.chat.assert_not_called()

@pytest.mark.parametrize('response',['not json','{"assessments":[]}',json.dumps({'assessments':[{'id':0,'status':'supported','evidence':[99]}]})])
def test_malformed_review_fails_closed(response):
    client=Mock();client.chat.return_value=(response,{})
    checks,error=assess('Use a daily irrigation schedule.',EVIDENCE,client,'test')
    assert checks[0]['status']=='insufficient_evidence' and error

def test_extractive_guidance_needs_no_model_judge():
    client=Mock()
    checks,error=assess(EVIDENCE[0]['guidance'],EVIDENCE,client,'test')
    assert checks[0]['status']=='supported'
    client.chat.assert_not_called()

def test_actual_pipeline_withholds_dosage():
    client=Mock();client.chat.return_value=('Apply 50 kg/ha urea.',{})
    result=advise({'question':'tomato irrigation'},client=client)
    assert result['withheld_claims']==1
    assert '50 kg' not in result['answer']

def test_no_evidence_does_not_generate_unsupported_advice():
    client=Mock()
    result=advise({'crop':'rice','question':'What soil pH is ideal?'},client=client)
    assert 'does not cover' in result['answer']
    client.chat.assert_not_called()

def test_translation_is_of_screened_advice():
    client=Mock();client.chat.side_effect=[('Apply 50 kg/ha urea.',{}),('मिट्टी की जाँच करें [Evidence 1]',{})]
    result=advise({'question':'irrigation','language':'hi'},client=client)
    assert result['translation'] and '50 kg' not in client.chat.call_args.args[1][1]['content']
