import csv
import io
from pathlib import Path

import pytest

from app.routes import transactions


def sample_row():
    path = Path(__file__).parents[1] / 'data/sample_transactions.csv'
    with path.open() as source:
        return next(csv.DictReader(source))


def csv_bytes(rows):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode()


@pytest.mark.parametrize('change', [
    {'amount': '-1'}, {'amount': 'inf'}, {'device_trust_score': '101'},
    {'channel': 'UNKNOWN'}, {'transaction_date': 'bad'}, {'is_foreign': 'maybe'},
])
def test_invalid_csv_row_is_rejected_atomically(client, auth_headers, change):
    first = sample_row()
    invalid = {**first, 'transaction_id': 'INVALID-SECOND', **change}
    response = client.post('/api/transactions/import', headers=auth_headers,
                           files={'file': ('input.csv', csv_bytes([first, invalid]), 'text/csv')})
    assert response.status_code == 400
    assert response.json()['detail'] == 'Invalid transaction at CSV row 3.'
    assert client.get('/api/transactions', headers=auth_headers).json() == []
    assert client.get('/api/cases', headers=auth_headers).json() == []


@pytest.mark.parametrize('content', [b'\xff\xfe', b'', b'unknown\nvalue\n'])
def test_invalid_csv_has_safe_error(client, auth_headers, content):
    response = client.post('/api/transactions/import', headers=auth_headers,
                           files={'file': ('input.csv', content, 'text/csv')})
    assert response.status_code == 400
    assert 'Traceback' not in response.text


def test_upload_size_limit(client, auth_headers, monkeypatch):
    monkeypatch.setattr(transactions, 'MAX_CSV_BYTES', 20)
    response = client.post('/api/transactions/import', headers=auth_headers,
                           files={'file': ('input.csv', b'x' * 21, 'text/csv')})
    assert response.status_code == 413


def test_import_valid_rows_and_duplicate_is_idempotent(client, auth_headers):
    content = csv_bytes([sample_row()])
    for expected in [{'imported': 1, 'skipped': 0, 'created_cases': 0},
                     {'imported': 0, 'skipped': 1, 'created_cases': 0}]:
        response = client.post('/api/transactions/import', headers=auth_headers,
                               files={'file': ('input.csv', content, 'text/csv')})
        assert response.status_code == 200
        assert response.json() == expected
