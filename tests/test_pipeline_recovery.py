"""Protocol/failure-recovery tests. Fixed outputs are not language-quality evidence."""
import json
from pathlib import Path
from unittest.mock import Mock
import pytest
from crop_advisory.engine import advise, Ollama
from crop_advisory.errors import AdvisoryError, ModelOutputTruncated
from crop_advisory.verification import split_claims, assess
from crop_advisory.translation import DIMENSIONS, translate_advisory, translation_chunks

EVIDENCE=[{'crop':'tomato','topic':'soil_moisture','guidance':'Check soil moisture and drainage before changing irrigation.','source':'Test fixture'}]
LANGUAGES={
 'kn':('Kannada','ನೀರಾವರಿಯನ್ನು ಬದಲಾಯಿಸುವ ಮೊದಲು ಮಣ್ಣಿನ ತೇವಾಂಶ ಮತ್ತು ನೀರು ಹರಿದುಹೋಗುವಿಕೆಯನ್ನು ಪರಿಶೀಲಿಸಿ. [Evidence 1]'),
 'hi':('Hindi','सिंचाई बदलने से पहले मिट्टी की नमी और जल निकासी की जाँच करें। [Evidence 1]')}


def test_headings_and_list_markers_are_not_claims():
    claims=split_claims('**Suggested checks**\n1. Check moisture at pH 6.8.\n2. Check drainage.\n**Limitations:**\nDo not infer a diagnosis.')
    assert claims==['Check moisture at pH 6.8.','Check drainage.','Do not infer a diagnosis.']


@pytest.mark.parametrize('case',json.loads((Path(__file__).parent/'fixtures/reported_claim_failures.json').read_text()),ids=lambda c:c['label'])
def test_uploaded_drafts_recover_from_incomplete_review(case):
    client=Mock();batches=[]
    def fake_review(model,messages,**kwargs):
        batch=json.loads(messages[1]['content'])['claims'];batches.append(batch)
        # Deliberately incomplete batch; singleton retries return the missing id.
        return json.dumps({'assessments':[{'id':batch[0]['id'],'status':'supported','evidence':[1],'reason':'synthetic protocol fixture'}]}),{}
    client.chat.side_effect=fake_review
    results,error=assess(case['draft'],case['evidence'],client,'fixture')
    assert error is None and results
    assert all(len(b)<=3 for b in batches)
    assert not any(r['claim'] in ('1.','2.','Observations','Evidence','Limitations','Suggested checks') for r in results)
    assert all(r['status']=='supported' for r in results)


def test_valid_assessment_survives_an_unresolved_neighbour():
    client=Mock();client.chat.side_effect=[(json.dumps({'assessments':[{'id':0,'status':'supported','evidence':[1],'reason':'fixture'}]}),{}),('not JSON',{})]
    results,error=assess('Check root-zone conditions.\nConfirm field conditions.',EVIDENCE,client,'fixture')
    assert results[0]['status']=='supported'
    assert results[1]['method']=='unavailable' and error


def test_conflicting_duplicate_id_needs_retry():
    client=Mock();client.chat.return_value=(json.dumps({'assessments':[{'id':0,'status':'supported','evidence':[1]},{'id':0,'status':'contradicted','evidence':[1]}]}),{})
    results,error=assess('Check root-zone conditions.',EVIDENCE,client,'fixture')
    assert results[0]['method']=='unavailable' and error


@pytest.mark.parametrize('code',LANGUAGES)
def test_each_language_retries_truncation_and_reviews_complete_output(code,monkeypatch):
    _,target=LANGUAGES[code]
    monkeypatch.setattr('crop_advisory.engine.select_evidence',lambda data:EVIDENCE)
    approved=json.dumps({'checks':dict.fromkeys(DIMENSIONS,True),'reason':'Synthetic schema fixture; not a human rating.'})
    client=Mock();client.chat.side_effect=[
        (EVIDENCE[0]['guidance'],{}),ModelOutputTruncated(2048),(target,{}),(approved,{})]
    result=advise({'question':'irrigation','language':code},client=client)
    assert result['translation']==target and result['translation_status']=='model_assessed'
    assert result['translation_metrics']['chunked']
    assert client.chat.call_args_list[1].kwargs['num_predict']==2048
    assert client.chat.call_args_list[2].kwargs['num_predict']==3072
    assert client.chat.call_args_list[3].kwargs['num_predict']==1024


@pytest.mark.parametrize('code',LANGUAGES)
def test_each_language_failed_retries_keep_english(code,monkeypatch):
    monkeypatch.setattr('crop_advisory.engine.select_evidence',lambda data:EVIDENCE)
    client=Mock();client.chat.side_effect=[(EVIDENCE[0]['guidance'],{}),ModelOutputTruncated(2048),ModelOutputTruncated(3072),ModelOutputTruncated(4096)]
    result=advise({'question':'irrigation','language':code},client=client)
    assert result['translation'] is None and result['answer']
    assert result['translation_status']=='unavailable'
    assert 'still truncated' in result['translation_failure_reason']


def test_multiple_chunks_are_complete_ordered_and_audited():
    original=('First paragraph has complete information. '*5)+'\n\n'+('Second paragraph has more complete information. '*5)
    chunks=translation_chunks(original)
    assert len(chunks)>1
    assert ' '.join(' '.join(chunks).split())==' '.join(original.split())
    client=Mock();client.chat.side_effect=[ModelOutputTruncated(2048)]+[(f'chunk-{i}',{'eval_count':10}) for i in range(len(chunks))]
    output,metrics=translate_advisory(original,'Hindi',client,'fixture')
    assert output=='\n\n'.join(f'chunk-{i}' for i in range(len(chunks)))
    assert len(metrics['attempts'])==len(chunks)+1


def test_model_client_uses_stage_budget_and_reports_truncation():
    client=Ollama();client.request=Mock(side_effect=[{}, {'done_reason':'length','message':{'content':'incomplete'},'eval_count':2048}])
    with pytest.raises(ModelOutputTruncated) as caught:
        client.chat('fixture',[],num_predict=2048,num_ctx=8192)
    assert caught.value.metrics['eval_count']==2048
    payload=client.request.call_args.args[1]
    assert payload['options']['num_predict']==2048 and payload['options']['num_ctx']==8192


def test_empty_truncated_response_still_triggers_retry_signal():
    client=Ollama();client.request=Mock(side_effect=[{}, {'done_reason':'length','message':{'content':''}}])
    with pytest.raises(ModelOutputTruncated):client.chat('fixture',[],num_predict=2048,num_ctx=8192)
