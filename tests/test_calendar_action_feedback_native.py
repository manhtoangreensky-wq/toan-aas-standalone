"""Temporary-DB native calendar GET envelopes -> actual integration action/toast."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def test_native_calendar_windows_retain_projection_and_localize_action_feedback(tmp_path,monkeypatch):
    spec=importlib.util.spec_from_file_location('calendar_native_fixture',ROOT/'tests'/'test_copyfast_auth_api.py')
    suite=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(suite)
    with suite.make_client(tmp_path,monkeypatch) as client:
        account={'email':'calendar-native-feedback@example.com','password':'valid-test-password-only','display_name':'QA Calendar'}
        assert client.post('/api/v1/auth/register',json=account).status_code==200
        login=client.post('/api/v1/auth/login',json={'email':account['email'],'password':account['password']})
        assert login.status_code==200
        csrf=login.json()['data']['csrf_token']
        for month in ['2026-11','2026-12']:
            created=client.post('/api/v1/campaigns',headers={'X-CSRF-Token':csrf},json={
                'title':'OWNER_NATIVE_CALENDAR_'+month,'destination_url':'https://example.com/calendar-native',
                'platform':'tiktok','objective':'traffic','scheduled_for':month+'-06T10:00','idempotency_key':'calendar-native-'+month,
            })
            assert created.status_code==200
        envelopes={}
        for action,month,status,platform in [
            ('campaign-calendar-filter','2026-11','draft','tiktok'),
            ('campaign-calendar-month','2026-12','all','all'),
            ('campaign-calendar-refresh','2026-11','all','all'),
        ]:
            response=client.get('/api/v1/campaign-calendar/window',params={'month':month,'status':status,'platform':platform})
            assert response.status_code==200
            assert response.headers['cache-control']=='no-store, private'
            assert response.json()['data']['summary']['total']==1
            assert response.json()['data']['items'][0]['title']=='OWNER_NATIVE_CALENDAR_'+month
            envelopes[action]=response.json()
        with sqlite3.connect(tmp_path/'copyfast-test.db') as connection:
            assert connection.execute('SELECT COUNT(*) FROM web_campaign_plans').fetchone()[0]==2
        helper=ROOT/'tests'/'helpers'/'render-native-calendar-feedback.mjs'
        for extra in [['--receipt-only'],[]]:
            result=subprocess.run(['node',str(helper),*extra],input=json.dumps(envelopes,ensure_ascii=False),text=True,encoding='utf-8',capture_output=True,cwd=ROOT,timeout=30)
            if extra and result.returncode==0:
                print(result.stdout.strip())
            assert result.returncode==0,result.stdout+result.stderr
