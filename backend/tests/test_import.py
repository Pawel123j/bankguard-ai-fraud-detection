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


LEGACY_COLUMNS = [
    'transaction_id', 'customer_id', 'amount', 'currency', 'merchant', 'merchant_category',
    'country', 'city', 'channel', 'transaction_date', 'is_foreign', 'is_night_transaction',
    'previous_failed_attempts', 'device_trust_score', 'status',
]


def test_csv_without_2026_11_signal_columns_still_imports(client, auth_headers):
    legacy = {key: sample_row()[key] for key in LEGACY_COLUMNS}
    response = client.post('/api/transactions/import', headers=auth_headers,
                           files={'file': ('legacy.csv', csv_bytes([legacy]), 'text/csv')})
    assert response.status_code == 200
    stored = client.get('/api/transactions', headers=auth_headers).json()[0]
    assert stored['is_new_payee'] is False
    assert stored['payee_account_age_days'] is None


def test_safe_account_scam_row_opens_a_critical_case(client, auth_headers):
    row = {**sample_row(), 'transaction_id': 'APP-SCAM-1', 'channel': 'TRANSFER', 'currency': 'PLN',
           'amount': '9000', 'is_new_payee': 'true', 'payee_account_age_days': '4',
           'remote_access_detected': 'yes', 'active_call_during_session': '1'}
    response = client.post('/api/transactions/import', headers=auth_headers,
                           files={'file': ('scam.csv', csv_bytes([row]), 'text/csv')})
    assert response.json() == {'imported': 1, 'skipped': 0, 'created_cases': 1}
    case = client.get('/api/cases', headers=auth_headers).json()[0]
    assert case['priority'] == 'CRITICAL'
    assert 'Pattern: possible bank-impersonation (safe account) scam' in case['transaction']['reasons']


def test_blik_channel_is_accepted_and_counted(client, auth_headers):
    row = {**sample_row(), 'transaction_id': 'BLIK-1', 'channel': 'BLIK', 'currency': 'PLN'}
    assert client.post('/api/transactions/import', headers=auth_headers,
                       files={'file': ('blik.csv', csv_bytes([row]), 'text/csv')}).status_code == 200
    stats = client.get('/api/dashboard/stats', headers=auth_headers).json()
    assert stats['channel_distribution']['BLIK'] == 1


@pytest.mark.parametrize('change', [{'payee_account_age_days': '-1'}, {'recent_sim_swap': 'maybe'}])
def test_invalid_new_signal_values_are_rejected(client, auth_headers, change):
    row = {**sample_row(), **change}
    response = client.post('/api/transactions/import', headers=auth_headers,
                           files={'file': ('bad.csv', csv_bytes([row]), 'text/csv')})
    assert response.status_code == 400
