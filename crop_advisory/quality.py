"""Measurement normalization and explicit quality states; no agronomic thresholds."""
import math
from datetime import datetime, timezone

SENSORS = ('moisture','temperature','ph')
UNITS = {'moisture':'% VWC','temperature':'°C','ph':'pH'}


def number(value, name, low, high):
    if value in (None,''):
        return None
    if isinstance(value,bool):
        raise ValueError(f'{name} must be a number.')
    try:
        result=float(value)
    except (ValueError,TypeError):
        raise ValueError(f'{name} must be a number.') from None
    if not math.isfinite(result) or not low<=result<=high:
        raise ValueError(f'{name} must be between {low} and {high}.')
    return result


def timestamp(value, name='timestamp'):
    if value in (None,''):
        return None
    if not isinstance(value,str):
        raise ValueError(f'{name} must be an ISO-8601 timestamp with a time zone.')
    try:
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError()
        return parsed.astimezone(timezone.utc)
    except ValueError:
        raise ValueError(f'{name} must be an ISO-8601 timestamp with a time zone.') from None


def calibration(value):
    if value in (None,'','unknown'):
        return None
    if value is True or str(value).lower()=='true':
        return True
    if value is False or str(value).lower()=='false':
        return False
    raise ValueError('calibrated must be true, false or unknown.')


def normalize_measurements(raw, now=None):
    now=now or datetime.now(timezone.utc)
    max_age=number(raw.get('max_reading_age_hours',24),'max_reading_age_hours',.01,8760)
    if max_age is None: max_age=24
    records={};values={};warnings=[]
    faults=raw.get('sensor_faults',{})
    if not isinstance(faults,dict):
        raise ValueError('sensor_faults must be an object.')
    for field in SENSORS:
        original=raw.get(field)
        unit=str(raw.get(field+'_unit') or UNITS[field]).strip()
        value=number(original,field,-10000,10000)
        if field=='moisture':
            if unit.lower() in ('fraction','m3/m3'):
                if value is not None and not 0<=value<=1: raise ValueError('Fractional moisture must be between 0 and 1.')
                value=None if value is None else value*100
            elif unit.lower() not in ('% vwc','vwc','%'):
                raise ValueError('Moisture unit must be % VWC or fraction (m3/m3), not raw sensor percentage.')
        elif field=='temperature':
            if unit.lower() in ('f','°f','fahrenheit'):
                value=None if value is None else (value-32)*5/9
            elif unit.lower() not in ('c','°c','celsius'):
                raise ValueError('Temperature unit must be °C or °F.')
        elif unit.lower()!='ph':
            raise ValueError('Soil pH unit must be pH.')
        limits={'moisture':(0,100),'temperature':(-20,70),'ph':(0,14)}[field]
        value=number(value,field,*limits)
        observed=timestamp(raw.get(field+'_timestamp') or raw.get('timestamp'),field+'_timestamp')
        age=(now-observed).total_seconds()/3600 if observed else None
        calibrated=calibration(raw.get(field+'_calibrated',raw.get('calibrated')))
        fault=faults.get(field,raw.get(field+'_fault',''))
        if not isinstance(fault,(str,bool)):
            raise ValueError(f'{field}_fault must be text or a boolean.')
        fault='' if fault in (False,'','false','False') else str(fault)[:200]
        states=[]
        if value is None: states.append('missing')
        else:
            if observed is None: states.append('timestamp_unknown')
            elif age < -5/60: states.append('future_timestamp')
            elif age > max_age: states.append('stale')
            if calibrated is False: states.append('uncalibrated')
            elif calibrated is None: states.append('calibration_unknown')
            if fault: states.append('reported_fault')
        excluded=any(s in states for s in ('future_timestamp','stale','uncalibrated','reported_fault'))
        usable=value if not excluded else None
        records[field]={'raw_value':original,'raw_unit':unit,'normalized_value':value,'unit':UNITS[field],
            'timestamp':observed.isoformat() if observed else None,'age_hours':round(age,3) if age is not None else None,
            'calibrated':calibrated,'sensor_id':str(raw.get(field+'_sensor_id') or raw.get('sensor_id',''))[:100],
            'fault':fault or None,'states':states or ['valid'],'usable':usable is not None}
        values[field]=usable
        if states and states!=['missing']:
            warnings.append(f"{field}: {', '.join(states)}" + ('; excluded from advice.' if excluded else '; interpret cautiously.'))
    return values,records,warnings,max_age


def normalize_weather(raw, now=None, max_age=24):
    now=now or datetime.now(timezone.utc)
    fields={'rainfall_24h_mm':(0,2000),'forecast_rainfall_mm':(0,2000),'humidity':(0,100)}
    weather={k:number(raw.get(k),k,*bounds) for k,bounds in fields.items()}
    observed=timestamp(raw.get('weather_timestamp'),'weather_timestamp')
    age=(now-observed).total_seconds()/3600 if observed else None
    supplied=any(v is not None for v in weather.values())
    states=[]
    if supplied:
        if observed is None: states.append('timestamp_unknown')
        elif age < -5/60: states.append('future_timestamp')
        elif age > max_age: states.append('stale')
    for k in ('weather_source','weather_notes'):
        text=str(raw.get(k) or '').strip()
        if len(text)>500: raise ValueError(f'{k} must be within 500 characters.')
        weather[k]=text
    weather.update(timestamp=observed.isoformat() if observed else None,age_hours=round(age,3) if age is not None else None,
        states=states or (['current'] if supplied else ['not_supplied']),usable=supplied and not any(s in states for s in ('stale','future_timestamp')),
        provenance='user-supplied offline observation or snapshot; no live weather API')
    return weather
