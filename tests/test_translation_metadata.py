"""Metadata and value preservation tests, not claims of model language quality."""
import json
import re
from pathlib import Path
from unittest.mock import Mock
import pytest
from crop_advisory.verification import split_claims, screened_answer, without_citations
from crop_advisory.translation import translate_advisory, protect_terms, restore_terms, normalize_equivalents, DIMENSIONS
from crop_advisory.engine import translation_checks, advise
from crop_advisory.errors import AdvisoryError

LANGUAGES={'hi':('Hindi','जाँच करें'),'kn':('Kannada','ಪರಿಶೀಲಿಸಿ'),'ta':('Tamil','சரிபார்க்கவும்'),'te':('Telugu','తనిఖీ చేయండి')}


def test_reported_draft_citations_attach_to_real_claims():
    data=json.loads((Path(__file__).parent/'fixtures/reported_citation_failure.json').read_text())
    claims=split_claims(data['draft'])
    assert len(claims)==3
    assert all(without_citations(c) for c in claims)
    assert '[Evidence 1]' in claims[0] and '[Evidence 2]' in claims[1]


def test_legacy_supported_citation_only_records_never_render_as_advice():
    data=json.loads((Path(__file__).parent/'fixtures/reported_citation_failure.json').read_text())
    answer=screened_answer(data['assessments'],[])
    assert not any(not without_citations(p) for p in answer.split('\n\n'))
    assert answer.count('[Evidence 2]')==1
    assert '[Evidence 1]' not in answer


@pytest.mark.parametrize('code',LANGUAGES)
def test_application_adds_citations_and_restores_protected_values(code):
    language,prefix=LANGUAGES[code]
    original='Check soil pH 6.5 to 7.5. [Evidence 2]'
    client=Mock()
    def fake(model,messages,**kwargs):
        assert '[Evidence' not in messages[1]['content']
        assert '6.5' not in messages[1]['content'] and 'pH' not in messages[1]['content']
        return prefix+' '+messages[1]['content'],{}
    client.chat.side_effect=fake
    text,metrics=translate_advisory(original,language,client,'fixture')
    checks=translation_checks(original,text,code)
    assert all(checks[k] for k in ('numbers_preserved','units_preserved','evidence_labels_preserved','target_script_present'))
    assert text.endswith('[Evidence 2]')
    assert metrics['citations_managed_by_application']


@pytest.mark.parametrize('translated',['मूल्य ६.५ और ७.५ [Evidence 1]','ಮೌಲ್ಯ ೬.೫ ಮತ್ತು ೭.೫ [Evidence 1]','மதிப்பு ௬.௫ மற்றும் ௭.௫ [Evidence 1]','విలువ ౬.౫ మరియు ౭.౫ [Evidence 1]'])
def test_equivalent_decimal_glyphs_preserve_numeric_values(translated):
    assert translation_checks('Values 6.5 and 7.5 [Evidence 1]',translated,'hi')['numbers_preserved']


def test_changed_or_duplicated_measurement_is_still_rejected():
    original='Values 6.5 and 7.5 [Evidence 1]'
    assert not translation_checks(original,'मूल्य ६.५ और ८.५ [Evidence 1]','hi')['numbers_preserved']
    assert not translation_checks(original,'मूल्य 6.5 6.5 7.5 [Evidence 1]','hi')['numbers_preserved']


def test_quantity_unit_pairs_and_compatibility_symbols():
    assert translation_checks('30 °C [Evidence 1]','तापमान ३० ℃ [Evidence 1]','hi')['units_preserved']
    assert not translation_checks('30 °C [Evidence 1]','तापमान ३० °F [Evidence 1]','hi')['units_preserved']


def test_omitted_and_duplicated_protected_terms_fail():
    masked,terms=protect_terms('pH 6.5')
    with pytest.raises(ValueError):restore_terms('',terms)
    with pytest.raises(ValueError):restore_terms(masked+' '+next(iter(terms)),terms)


def test_unexpected_citation_is_not_silently_repaired():
    client=Mock();client.chat.return_value=('जाँच करें [Evidence 99]',{})
    with pytest.raises(AdvisoryError) as exc:
        translate_advisory('Check drainage. [Evidence 1]','Hindi',client,'fixture')
    assert 'unexpected source' in str(exc.value)
    assert exc.value.metrics['attempts']


def test_missing_protected_values_retries_and_preserves_audit():
    client=Mock();calls=[]
    def fake(model,messages,**kwargs):
        calls.append(kwargs['num_predict'])
        if len(calls)==1:return 'मिट्टी की जाँच करें',{}
        return 'जाँच करें '+messages[1]['content'],{}
    client.chat.side_effect=fake
    text,metrics=translate_advisory('Check pH 6.5. [Evidence 1]','Hindi',client,'fixture')
    assert calls==[2048,3072] and 'pH 6.5' in text
    assert metrics['attempts'][0]['status']=='invalid_protected_values'
    assert 'candidate_text_audit_only' in metrics['attempts'][0]


def test_meaning_change_still_withholds_translation(monkeypatch):
    evidence=[{'crop':'tomato','topic':'soil_moisture','guidance':'Check moisture.','source':'Fixture'}]
    monkeypatch.setattr('crop_advisory.engine.select_evidence',lambda data:evidence)
    client=Mock();client.chat.side_effect=[('Check moisture.',{}),('जाँच करें',{}),(json.dumps({'checks':{**dict.fromkeys(DIMENSIONS,True),'negation':False},'reason':'fixture meaning change'}),{})]
    result=advise({'question':'water','language':'hi'},client=client)
    assert result['translation'] is None and result['answer']
    assert result['translation_review']['checks']['negation'] is False
