"""Local presentation coverage and protected-value checks, not fluency scores."""
import json
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import Mock
import pytest
from crop_advisory.engine import LANGUAGES, advise, translation_checks
from crop_advisory.translation import translate_advisory

ROOT=Path(__file__).resolve().parents[1]
CATALOG=json.loads((ROOT/'web/hi.json').read_text())


def test_all_bundled_reference_text_has_hindi_presentation():
    for filename in ('tomato_knowledge.json','crop_knowledge.json'):
        for source in json.loads((ROOT/'data'/filename).read_text()):
            for key in ('source','guidance'):
                assert source[key] in CATALOG
                assert any('\u0900'<=c<='\u097f' for c in CATALOG[source[key]])
            # Localized reference wording must not change or duplicate measurements.
            checks=translation_checks(source['guidance'],CATALOG[source['guidance']],'hi')
            assert checks['numbers_preserved'] and checks['units_preserved']


def test_every_static_page_label_and_placeholder_is_catalogued():
    allowed={'CropAdvisory · Field assistant','◉ CropAdvisory','% VWC','°C','°F','❧','↗'}
    class Page(HTMLParser):
        def handle_data(self,text):
            text=text.strip()
            assert not text or text in allowed or text in CATALOG, text
        def handle_starttag(self,tag,attrs):
            placeholder=dict(attrs).get('placeholder')
            assert not placeholder or placeholder in CATALOG or placeholder.startswith('2026-'),placeholder
    Page().feed((ROOT/'web/index.html').read_text())


@pytest.mark.parametrize('crop,expected',[('tomato','टमाटर'),('tomatoes','टमाटर'),('rice','धान'),('wheat','गेहूँ'),('cotton','कपास')])
def test_hindi_crop_names_restored_before_semantic_assessment(crop,expected):
    client=Mock()
    client.chat.side_effect=lambda model,messages,**kwargs:('जाँच करें '+messages[1]['content'],{})
    original=f'Check {crop} soil pH 6.5. [Evidence 1]'
    result,_=translate_advisory(original,'Hindi',client,'fixture')
    assert expected in result and crop not in result
    checks=translation_checks(original,result,'hi')
    assert all(checks[key] for key in ('numbers_preserved','units_preserved','evidence_labels_preserved'))


@pytest.mark.parametrize('language',['kn','ta','te'])
def test_removed_languages_rejected_before_any_model_call(language):
    assert set(LANGUAGES)=={'en','hi'}
    client=Mock()
    with pytest.raises(ValueError,match='Unsupported language'):
        advise({'language':language,'question':'irrigation'},client=client)
    client.chat.assert_not_called()
