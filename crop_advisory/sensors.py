"""Validated imports for logged sensor measurements. No live device is assumed."""
import csv
from .engine import validate_input


def read_csv(stream):
    reader = csv.DictReader(stream)
    required = {'crop','moisture','temperature','ph'}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise ValueError('CSV must include crop, moisture, temperature, ph headers.')
    for row_number, row in enumerate(reader,2):
        try:
            if None in row:
                raise ValueError('Too many CSV columns.')
            yield {'row':row_number,'timestamp':row.get('timestamp',''),
                   'input':validate_input(row),'error':None}
        except (ValueError,TypeError) as exc:
            yield {'row':row_number,'input':None,'error':str(exc)}
