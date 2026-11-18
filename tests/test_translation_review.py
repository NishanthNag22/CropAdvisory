import json
from unittest.mock import Mock
import pytest
from crop_advisory.translation import semantic_review, unit_checks, DIMENSIONS
from crop_advisory.engine import advise, AdvisoryError


def review_response(**changes):
    return json.dumps({'checks':{**dict.fromkeys(DIMENSIONS,True),**changes},'reason':'fixture assessment'})

def test_changed_unit_and_quantity_association_detected():
    assert not unit_checks('30 °C, 32 %','30 °F, 32 %')['units_preserved']
    assert not unit_checks('30 °C, 32 %','32 °C, 30 %')['units_preserved']

@pytest.mark.parametrize('dimension',DIMENSIONS)
def test_each_failed_semantic_dimension_withholds(dimension):
    client=Mock();client.chat.return_value=(review_response(**{dimension:False}),{})
    result=semantic_review('Do not irrigate now.','अभी सिंचाई करें।','Hindi','rice',client,'test')
    assert not result['accepted']

@pytest.mark.parametrize('bad',['{}','not-json',json.dumps({'checks':dict.fromkeys(DIMENSIONS,'true')})])
def test_malformed_reviews_fail_closed(bad):
    client=Mock();client.chat.return_value=(bad,{})
    assert not semantic_review('test','परीक्षण','Hindi','rice',client,'test')['accepted']

def test_pipeline_returns_english_when_translation_loses_number():
    client=Mock();client.chat.side_effect=[('Apply 50 kg/ha urea.',{}),('मिट्टी 999 [Evidence 1]',{})]
    result=advise({'question':'irrigation','language':'hi'},client=client)
    assert result['translation'] is None and result['answer']
    assert result['translation_status']=='withheld'

def test_pipeline_failed_semantic_review_preserves_english():
    client=Mock();client.chat.side_effect=[('Apply 50 kg/ha urea.',{}),('मिट्टी [Evidence 1]',{}),(review_response(negation=False),{})]
    result=advise({'question':'irrigation','language':'hi'},client=client)
    assert result['translation'] is None and result['translation_review']['checks']['negation'] is False

def test_translation_service_failure_preserves_english():
    client=Mock();client.chat.side_effect=[('Apply 50 kg/ha urea.',{}),AdvisoryError('unavailable')]
    result=advise({'question':'irrigation','language':'hi'},client=client)
    assert result['translation_status']=='unavailable' and result['answer']
