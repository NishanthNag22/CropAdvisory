import sys
from pathlib import Path
from unittest.mock import Mock
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from crop_advisory.engine import validate_input, sensor_summary, advise, translation_checks, AdvisoryError, Ollama

@pytest.mark.parametrize('field,value', [('ph',15),('ph',True),('moisture',-1),('temperature',float('nan')),('temperature',float('inf'))])
def test_bad_readings(field,value):
    with pytest.raises(ValueError):
        validate_input({'question':'irrigation', field:value})

def test_summary_preserves_missing_and_units():
    summary=sensor_summary(validate_input({'moisture':0,'ph':6.8}))
    assert '0 % volumetric' in summary and 'temperature: not supplied' in summary and '6.8 pH' in summary

def test_evidence_mode_does_not_invoke_model():
    client=Mock()
    result=advise({'question':'irrigation'},client=client,mode='evidence')
    client.chat.assert_not_called()
    assert result['model'] is None and result['evidence']

def test_model_error_never_becomes_fake_advisory():
    client=Mock();client.chat.side_effect=AdvisoryError('offline')
    with pytest.raises(AdvisoryError):
        advise({'question':'irrigation'},client=client)

def test_translation_rejects_lost_numbers():
    check=translation_checks('pH 6.5 to 7.5 [Evidence 1]','मिट्टी 6.5 [Evidence 1]','hi')
    assert not check['numbers_preserved'] and check['target_script_present']

def test_translation_keeps_script_and_labels():
    check=translation_checks('6.5 [Evidence 1]','मिट्टी 6.5 [Evidence 1]','hi')
    assert check['numbers_preserved'] and check['evidence_labels_preserved']

def test_no_external_model_host():
    with pytest.raises(ValueError):
        Ollama('https://example.com')

@pytest.mark.parametrize('crop',['tomato','rice','wheat','cotton'])
def test_crop_filter(crop):
    result=advise({'crop':crop,'question':'irrigation water','moisture':32},mode='evidence')
    assert result['evidence']
    assert all(e['crop']==crop for e in result['evidence'])
    if crop != 'tomato':
        assert '6.5' not in result['answer']

def test_unknown_crop_rejected():
    with pytest.raises(ValueError):
        validate_input({'crop':'banana','question':'irrigation'})

def test_unsupported_topic_has_no_made_up_guidance():
    result=advise({'crop':'rice','question':'What pH is ideal?'},mode='evidence')
    assert result['evidence']==[]

@pytest.mark.parametrize('crop',['rice','wheat','cotton'])
def test_growth_stage_guidance(crop):
    result=advise({'crop':crop,'question':'water at flowering stage'},mode='evidence')
    assert 'growth_stage' in [e['topic'] for e in result['evidence']]
