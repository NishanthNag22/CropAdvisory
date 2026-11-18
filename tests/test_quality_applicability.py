from datetime import datetime, timezone, date
import pytest
from crop_advisory.engine import validate_input, advise
from crop_advisory.quality import normalize_measurements
from crop_advisory.applicability import assess_source, screen_sources
NOW=datetime(2026,11,18,12,tzinfo=timezone.utc)

def test_normalize_units_before_range_validation():
    data=validate_input({'temperature':86,'temperature_unit':'F','moisture':.32,'moisture_unit':'fraction'},now=NOW)
    assert data['temperature']==30 and data['moisture']==32

@pytest.mark.parametrize('stamp',['2026-11-18T12:00:00','bad'])
def test_timestamp_requires_timezone(stamp):
    with pytest.raises(ValueError):validate_input({'ph':6.8,'timestamp':stamp},now=NOW)

@pytest.mark.parametrize('extra,state',[
 ({'timestamp':'2026-11-16T12:00:00Z'},'stale'),
 ({'timestamp':'2026-11-19T12:00:00Z'},'future_timestamp'),
 ({'calibrated':False},'uncalibrated'),
 ({'sensor_faults':{'moisture':'disconnected'}},'reported_fault')])
def test_unreliable_measurements_withheld(extra,state):
    data=validate_input({'question':'irrigation','moisture':32,**extra},now=NOW)
    assert data['moisture'] is None
    assert data['sensor_quality']['moisture']['normalized_value']==32
    assert state in data['sensor_quality']['moisture']['states']

def test_timezone_offsets_and_calibration():
    data=validate_input({'moisture':32,'timestamp':'2026-11-18T17:30:00+05:30','calibrated':'true'},now=NOW)
    assert data['sensor_quality']['moisture']['states']==['valid']

def test_weather_freshness_and_unknown():
    data=validate_input({'question':'water','rainfall_24h_mm':12,'weather_timestamp':'2026-11-16T12:00:00Z'},now=NOW)
    assert not data['weather']['usable'] and data['weather']['states']==['stale']

@pytest.mark.parametrize('key,value',[('humidity',101),('rainfall_24h_mm',-1),('moisture_unit','raw')])
def test_weather_and_units_invalid(key,value):
    with pytest.raises(ValueError):validate_input({'question':'water',key:value},now=NOW)

SOURCE={'crop':'rice','region':'Tamil Nadu, India','regions':['tamil nadu'],'seasons':['kharif'],
        'production_systems':['transplanted'],'reviewed_on':'2026-11-18','published_on':None}

def test_scope_mismatch_is_excluded():
    check=assess_source(SOURCE,{'crop':'rice','region':'Karnataka'},date(2026,11,18))
    assert not check['eligible'] and check['checks']['region']=='mismatch'

@pytest.mark.parametrize('context',[{'season':'rabi'},{'production_system':'direct seeded'}])
def test_season_and_production_mismatch(context):
    assert not assess_source(SOURCE,{'crop':'rice',**context},date(2026,11,18))['eligible']

def test_unknown_metadata_not_falsely_verified():
    check=assess_source(SOURCE,{'crop':'rice'},date(2026,11,18))
    assert check['eligible'] and check['checks']['published_on']=='unknown'
    assert check['checks']['region']=='unknown'

def test_expired_source_not_retrieved():
    source=dict(SOURCE,valid_until='2026-01-01')
    accepted,excluded=screen_sources([source],{'crop':'rice'},date(2026,11,18))
    assert not accepted and excluded

def test_pipeline_uses_scope_filter():
    result=advise({'crop':'rice','region':'Karnataka','question':'irrigation'},mode='evidence')
    assert not result['evidence'] and result['excluded_sources']

def test_csv_history_reports_suspected_stuck_sensor():
    import io
    from crop_advisory.sensors import read_csv
    csv='crop,moisture,temperature,ph,question,sensor_id\n'+('rice,32,,,water,device-1\n'*5)
    rows=list(read_csv(io.StringIO(csv)))
    assert 'reported_fault' in rows[-1]['input']['sensor_quality']['moisture']['states']
    assert 'suspected stuck' in rows[-1]['input']['sensor_quality']['moisture']['fault']

def test_csv_devices_do_not_share_fault_history():
    import io
    from crop_advisory.sensors import read_csv
    csv='crop,moisture,temperature,ph,question,sensor_id\n'+''.join(f'rice,32,,,water,device-{i}\n' for i in range(5))
    rows=list(read_csv(io.StringIO(csv)))
    assert all('reported_fault' not in r['input']['sensor_quality']['moisture']['states'] for r in rows)

def test_stale_readings_not_in_decision_context():
    from crop_advisory.engine import build_messages
    data=validate_input({'question':'water','moisture':32,'timestamp':'2026-11-10T12:00:00Z'},now=NOW)
    import json
    content=json.loads(build_messages(data,[])[1]['content'])
    assert 'normalized_value' not in content['sensor_quality']['moisture']
    assert 'moisture: not supplied' in content['sensor_summary']
