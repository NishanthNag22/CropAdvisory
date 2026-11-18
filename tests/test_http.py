import json
import threading
from http.server import ThreadingHTTPServer
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from unittest.mock import patch
import pytest
from app import Handler
from crop_advisory.engine import Ollama, AdvisoryError, translation_checks

@pytest.fixture(scope='module')
def server_url():
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    yield f'http://127.0.0.1:{server.server_port}'
    server.shutdown();server.server_close();thread.join()


def post(url,payload,headers=None):
    return urlopen(Request(url+'/api/advice',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json',**(headers or {})}),timeout=5)


def test_page_and_assets(server_url):
    for path in ['/', '/app.js', '/style.css','/api/health']:
        with urlopen(server_url+path) as response:
            assert response.status==200
            assert response.headers['X-Content-Type-Options']=='nosniff'

@pytest.mark.parametrize('crop',['tomato','rice','wheat','cotton'])
def test_http_advice_crop_isolation(server_url,crop):
    with post(server_url,{'crop':crop,'question':'irrigation','mode':'evidence'}) as response:
        result=json.load(response)
    assert result['mode']=='evidence'
    assert all(e['crop']==crop for e in result['evidence'])


def test_bad_input_is_http_400(server_url):
    with pytest.raises(HTTPError) as exc:
        post(server_url,{'ph':15,'question':'soil'})
    assert exc.value.code==400


def test_cross_origin_request_rejected(server_url):
    with pytest.raises(HTTPError) as exc:
        post(server_url,{'question':'water','mode':'evidence'},{'Origin':'https://untrusted.example'})
    assert exc.value.code==403


def test_cloud_model_rejected_before_network():
    client=Ollama()
    with patch.object(client,'request') as request:
        with pytest.raises(AdvisoryError):
            client.chat('test:cloud',[])
        request.assert_not_called()


def test_remote_alias_model_rejected():
    client=Ollama()
    with patch.object(client,'request',return_value={'remote_host':'https://remote.example'}):
        with pytest.raises(AdvisoryError):
            client.chat('alias',[])


def test_malformed_message_is_actionable_error():
    client=Ollama()
    with patch.object(client,'request',side_effect=[{}, {'message':[]} ]):
        with pytest.raises(AdvisoryError):
            client.chat('test-model',[])


def test_translation_added_measurement_is_rejected():
    checks=translation_checks('Check pH 6.5 [Evidence 1]','मिट्टी 6.5 और 40 [Evidence 1]','hi')
    assert not checks['numbers_preserved'] and checks['added_numbers']==['40']
