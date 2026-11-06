"""Actual isolated native response -> actual UI renderer; no fabricated final receipt."""
import importlib.util
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def test_native_review_receipt_renders_customer_copy_and_localized_system_guidance(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        'native_review_fixture', ROOT / 'tests' / 'test_copyfast_content_studio.py'
    )
    suite = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(suite)
    with suite.make_client(tmp_path, monkeypatch) as client:
        csrf = suite.register_and_login(client, 'native-review-locale@example.com')
        before = suite.prompt_pack_storage_counts(tmp_path / 'content-studio-test.db')
        response = client.post(
            '/api/v1/content-studio/tools/publish-review-pack',
            headers={'X-CSRF-Token': csrf},
            json={
                'title': 'CUSTOMER_NATIVE_TITLE',
                'caption': 'CUSTOMER_NATIVE_CAPTION',
                'hashtags': ['#CUSTOMERNATIVE'],
                'cta': 'CUSTOMER_NATIVE_CTA',
                'source_prompt': 'CUSTOMER_NATIVE_SOURCE',
            },
        )
        assert response.status_code == 200
        assert response.json()['ok'] is True
        data = response.json()['data']
        assert suite.prompt_pack_storage_counts(tmp_path / 'content-studio-test.db') == before
        for key, value in data.items():
            if key not in {'package', 'execution'}:
                assert value is False, key
        rendered = subprocess.run(
            ['node', str(ROOT / 'tests' / 'helpers' / 'render-native-publish-review.mjs')],
            input=json.dumps(data, ensure_ascii=False), text=True, encoding='utf-8',
            capture_output=True, cwd=ROOT, timeout=30,
        )
        assert rendered.returncode == 0, rendered.stdout + rendered.stderr
