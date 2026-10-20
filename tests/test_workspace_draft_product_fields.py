"""Native drafts retain product text, without gaining execution authority."""
import uuid
from contextlib import contextmanager

import pytest

from tests.test_copyfast_auth_api import make_client


@contextmanager
def signed_client(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        identity = {"email": f"product-draft-{uuid.uuid4()}@qa.invalid", "password": "qa-only-long-passphrase"}
        assert client.post("/api/v1/auth/register", json=identity).status_code == 200
        login = client.post("/api/v1/auth/login", json=identity)
        assert login.status_code == 200
        yield client, {"X-CSRF-Token": login.json()["data"]["csrf_token"]}


@pytest.mark.parametrize("feature", ["music_song", "music_background", "voice_tts"])
def test_product_choices_survive_create_read_update_and_replay(tmp_path, monkeypatch, feature):
    with signed_client(tmp_path, monkeypatch) as (client, headers):
        values = {"brief": "Ý tưởng QA", "lyrics": "Dòng một 🎵\nDòng hai 中文",
                  "vocal_mode": "duet", "default_voice_gender": "female",
                  "volume_percent": "0", "source_language": "auto"}
        payload = {"feature_key": feature, "title": "Bản nháp QA", "input": values,
                   "idempotency_key": f"product-draft-{uuid.uuid4()}"}
        assert client.post("/api/v1/workspace/drafts", json=payload).status_code == 403
        created = client.post("/api/v1/workspace/drafts", headers=headers, json=payload)
        assert created.status_code == 200, created.text
        draft_id = created.json()["data"]["item"]["id"]
        replay = client.post("/api/v1/workspace/drafts", headers=headers, json=payload)
        assert replay.json()["data"]["item"]["id"] == draft_id
        assert client.get(f"/api/v1/workspace/drafts/{draft_id}").json()["data"]["item"]["input"] == values
        updated_values = {**values, "lyrics": "Lời đã sửa 🎶", "default_voice_gender": "male", "source_language": "vi"}
        updated = client.patch(f"/api/v1/workspace/drafts/{draft_id}", headers=headers,
                               json={"input": updated_values, "idempotency_key": f"product-update-{uuid.uuid4()}"})
        assert updated.status_code == 200, updated.text
        assert client.get(f"/api/v1/workspace/drafts/{draft_id}").json()["data"]["item"]["input"] == updated_values


@pytest.mark.parametrize("bad,status", [
    ({"lyrics": {"nested": "no"}}, 422), ({"vocal_mode": False}, 422),
    ({"volume_percent": 0}, 422), ({"lyrics": "x" * 4001}, 422),
    ({"lyrics": "x" * 4000, "brief": "y" * 4000, "notes": "z" * 4000, "script": "w" * 4000}, 413),
    ({"voice_profile_id": "profile-qa"}, 422), ({"upload_ids": "file-qa"}, 422),
    ({"consent": "true"}, 422), ({"web_quote_receipt": "qa-receipt"}, 422),
    ({"provider": "qa"}, 422), ({"canonical_user_id": "qa"}, 422),
])
def test_new_text_fields_do_not_relax_native_draft_guards(tmp_path, monkeypatch, bad, status):
    with signed_client(tmp_path, monkeypatch) as (client, headers):
        response = client.post("/api/v1/workspace/drafts", headers=headers,
                               json={"feature_key": "music_song", "title": "QA rejected input", "input": bad,
                                     "idempotency_key": f"product-reject-{uuid.uuid4()}"})
        assert response.status_code == status, response.text
        assert client.get("/api/v1/workspace/drafts").json()["data"]["items"] == []
