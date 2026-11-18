"""Validated imports for logged sensor measurements. No live device is assumed."""
import csv
from .engine import validate_input


def read_csv(stream):
    reader = csv.DictReader(stream)
    required = {'crop','moisture','temperature','ph'}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise ValueError('CSV must include crop, moisture, temperature, ph headers.')
    history={}
    for row_number, row in enumerate(reader,2):
        try:
            if None in row:
                raise ValueError('Too many CSV columns.')
            flags={}
            for field in ('moisture','temperature','ph'):
                sensor_id=row.get(field+'_sensor_id') or row.get('sensor_id')
                if not sensor_id or row.get(field) in (None,''): continue
                key=(sensor_id,field)
                record=history.setdefault(key,[])
                from .quality import timestamp
                stamp=timestamp(row.get(field+'_timestamp') or row.get('timestamp'))
                value=float(row[field])
                unit=row.get(field+'_unit','')
                if record and stamp and record[-1][1] and stamp<=record[-1][1]:
                    flags[field]='duplicate or out-of-order timestamp'
                record.append((value,stamp,unit));del record[:-5]
                if len(record)==5 and len({(r[0],r[2]) for r in record})==1:
                    flags[field]='suspected stuck sensor: five identical samples; stable conditions are also possible'
            if flags:
                row['sensor_faults']=flags
            yield {'row':row_number,'timestamp':row.get('timestamp',''),
                   'input':validate_input(row),'raw_input':dict(row),'error':None}
        except (ValueError,TypeError) as exc:
            flags={}
            for field in ('moisture','temperature','ph'):
                sensor_id=row.get(field+'_sensor_id') or row.get('sensor_id')
                if not sensor_id or row.get(field) in (None,''): continue
                key=(sensor_id,field)
                record=history.setdefault(key,[])
                from .quality import timestamp
                stamp=timestamp(row.get(field+'_timestamp') or row.get('timestamp'))
                value=float(row[field])
                unit=row.get(field+'_unit','')
                if record and stamp and record[-1][1] and stamp<=record[-1][1]:
                    flags[field]='duplicate or out-of-order timestamp'
                record.append((value,stamp,unit));del record[:-5]
                if len(record)==5 and len({(r[0],r[2]) for r in record})==1:
                    flags[field]='suspected stuck sensor: five identical samples; stable conditions are also possible'
            if flags:
                row['sensor_faults']=flags
            yield {'row':row_number,'input':None,'error':str(exc)}
