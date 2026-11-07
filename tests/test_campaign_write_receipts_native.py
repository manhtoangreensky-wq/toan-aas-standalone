"""Temporary native writes -> original envelopes -> complete client action handlers."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_campaign_native_receipts_keep_owner_csrf_idempotency_and_client_projection(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('campaign_receipt_fixture', ROOT/'tests'/'test_copyfast_auth_api.py')
    suite = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(suite)
    with suite.make_client(tmp_path, monkeypatch) as client:
        account = {'email': 'campaign-receipt-qa@example.com', 'password': 'isolated-test-password-only'}
        assert client.post('/api/v1/auth/register', json=account).json()['ok'] is True
        login = client.post('/api/v1/auth/login', json=account)
        assert login.status_code == 200
        headers = {'X-CSRF-Token': login.json()['data']['csrf_token']}
        fields = {'title': 'OWNER_NATIVE_CAMPAIGN', 'destination_url': 'https://example.com/native-campaign',
                  'platform': 'website', 'objective': 'traffic', 'scheduled_for': ''}
        create_body = {**fields, 'idempotency_key': 'campaign-native-create-0001'}
        assert client.post('/api/v1/campaigns', json=create_body).status_code == 403
        response = client.post('/api/v1/campaigns', headers=headers, json=create_body)
        assert response.status_code == 200 and response.json()['ok'] is True
        created = response.json()
        assert created['data']['item']['revision'] == 1
        assert client.post('/api/v1/campaigns', headers=headers, json=create_body).json() == created
        plan_id = created['data']['item']['id']
        edit_fields = {**fields, 'title': 'OWNER_NATIVE_CAMPAIGN_EDIT'}
        edited = client.patch(f'/api/v1/campaigns/{plan_id}', headers=headers,
                              json={**edit_fields, 'idempotency_key': 'campaign-native-edit-0001'}).json()
        assert edited['ok'] is True and edited['data']['item']['revision'] == 2
        status_fields = {'plan_id': plan_id, 'approval_status': 'review', 'review_note': 'OWNER_NATIVE_NOTE'}
        status = client.post(f'/api/v1/campaigns/{plan_id}/status', headers=headers,
                             json={**status_fields, 'idempotency_key': 'campaign-native-status-0001'}).json()
        assert status['ok'] is True and status['data']['item']['revision'] == 3
        samples = {'campaign-create': {'fields': fields, 'response': created},
                   'campaign-update': {'fields': {**edit_fields, 'plan_id': plan_id}, 'response': edited},
                   'campaign-update-status': {'fields': status_fields, 'response': status}}
        with sqlite3.connect(tmp_path/'copyfast-test.db') as connection:
            assert connection.execute('SELECT COUNT(*) FROM web_campaign_plans').fetchone()[0] == 1
        # A second signed Web account is intentionally not linked to Telegram.
        assert client.post('/api/v1/auth/logout', headers=headers).status_code == 200
        other = {'email': 'campaign-other-qa@example.com', 'password': 'isolated-test-password-only'}
        assert client.post('/api/v1/auth/register', json=other).json()['ok'] is True
        login_other = client.post('/api/v1/auth/login', json=other)
        other_headers = {'X-CSRF-Token': login_other.json()['data']['csrf_token']}
        assert client.get('/api/v1/campaigns').json()['data']['items'] == []
        rejected = client.post(f'/api/v1/campaigns/{plan_id}/status', headers=other_headers,
                               json={**status_fields, 'idempotency_key': 'campaign-other-status-0001'}).json()
        assert rejected['ok'] is False and rejected['error_code'] == 'CAMPAIGN_PLAN_NOT_FOUND'
        helper = ROOT/'tests'/'helpers'/'render-native-campaign-writes.mjs'
        result = subprocess.run(['node', str(helper)], input=json.dumps(samples, ensure_ascii=False),
                                text=True, encoding='utf-8', capture_output=True, cwd=ROOT, timeout=30)
        assert result.returncode == 0, result.stdout+result.stderr
        print(result.stdout.strip())
