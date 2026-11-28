"""End-to-end tests for Realtime Translate bridges, multi-worker persistence, CORS & Chrome Direct UI."""

from __future__ import annotations

import asyncio
import importlib
from pathlib import Path

from fastapi.testclient import TestClient
import httpx

import copyfast_bridge
import copyfast_pages
import copyfast_realtime_translate as rt


def test_bridge_preserves_bounded_tts_audio_b64_while_truncating_normal_strings():
    long_audio = "A" * 18_000
    long_note = "B" * 10_000
    payload = {
        "ok": True,
        "events": [
            {"type": "tts.audio", "audio_b64": long_audio, "format": "mp3"},
            {"type": "stt.final", "source_text": long_note},
        ],
    }
    sanitized = copyfast_bridge._sanitize_data(payload)
    assert len(sanitized["events"][0]["audio_b64"]) == 18_000
    assert len(sanitized["events"][1]["source_text"]) == copyfast_bridge._MAX_SAFE_STRING_LENGTH


def test_cors_allows_chrome_extension_origin_while_preserving_canonical_origins(monkeypatch):
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    app_mod = importlib.import_module("app")
    assert app_mod._origins() == ["https://app.toanaas.vn"]

    client = TestClient(app_mod.app)
    ext_origin = "chrome-extension://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    resp = client.options(
        "/api/v1/live-translate/sessions",
        headers={
            "Origin": ext_origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,X-CSRF-Token",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == ext_origin
    assert resp.headers.get("access-control-allow-credentials") == "true"


def test_multiworker_sqlite_persistence_and_canonical_wallet_admission(tmp_path, monkeypatch):
    db_file = tmp_path / "rt_webapp.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_file))
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_file))
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(db_file))
    monkeypatch.setenv("TOAN_AAS_ENV", "production")
    monkeypatch.setenv("REALTIME_STREAM_SECRET", "webapp-test-stream-secret-32-bytes")
    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "http://127.0.0.1:8080")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "test-bridge-token-32-bytes-minimum")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "test-hmac-secret-32-bytes-minimum")

    bridge_calls = []

    async def fake_bridge(method, path, payload=None, params=None, actor_id=None, **kwargs):
        bridge_calls.append((method, path, actor_id, payload, params))
        if path == "/internal/v1/wallet":
            return {"ok": True, "data": {"balance_xu": 250 if actor_id == "777888999" else 0}}
        if path == "/internal/v1/realtime/process-chunk":
            return {
                "ok": True,
                "events": [
                    {"type": "stt.final", "source_text": "Hello"},
                    {"type": "translation.final", "translated_text": "Xin chao"},
                ],
            }
        if path == "/internal/v1/realtime/settle":
            return {"ok": True, "amount_xu": 4, "balance_after": 246, "status": "settled"}
        return {"ok": False}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", fake_bridge)

    class DummyReq:
        pass

    async def _run():
        # Paid linked user admitted using Bot wallet canonical_user_id
        paid_acc = {"id": "web_uuid_1", "canonical_user_id": "777888999"}
        req = rt.CreateSessionRequest(source_language="en", target_language="vi", mode="LIVE_DUB_BILINGUAL")
        created = await rt.create_live_translate_session(req, DummyReq(), account=paid_acc)
        sid = created.session_id

        # Emulate another uvicorn worker with empty RAM registry
        rt._ACTIVE_SESSIONS.clear()
        rt._ACTIVE_INGRESS_BUFFERS.clear()
        rt._SESSION_CANONICAL_ACTORS.clear()

        status = await rt.get_session_status(sid, account=paid_acc)
        assert status["ok"] is True
        assert status["session_id"] == sid

        # Canonical actor_id forwarded to Bot /process-chunk
        sess = rt._get_or_load_session(sid)
        assert sess is not None
        seg = rt.SpeechSegment(
            segment_id="seg_mw_1",
            sequence_start=1,
            sequence_end=1,
            start_ms=0,
            end_ms=500,
            pcm_bytes=b"\x20\x00" * 1600,
        )
        res = await rt.forward_segment_to_bot(sess, 1, seg)
        assert res.status == "success"
        assert any(c[1] == "/internal/v1/realtime/process-chunk" and c[2] == "777888999" for c in bridge_calls)

        # Simulate translated segment chars & stop settlement
        rt._SESSION_UNBILLED_CHARS[sid] = 50
        rt._SESSION_BOT_BRIDGE_OK[sid] = 1
        rt._persist_realtime_session(sess)
        rt._ACTIVE_SESSIONS.clear()

        stopped = await rt.stop_session(sid, account=paid_acc)
        assert stopped["ok"] is True
        assert stopped["state"] == "ended"
        assert stopped["settled_xu"] == 4
        assert stopped["balance_after"] == 246

    asyncio.run(_run())


def test_subdub_shell_includes_live_studio_and_excludes_from_auth_split():
    app_mod = importlib.import_module("app")
    subdub_resp = app_mod._attach_live_translate_studio(copyfast_pages.render_portal("/subdub"), "/subdub")
    subdub_html = subdub_resp.body.decode("utf-8")
    assert "/static/portal/live-translate-studio.js" in subdub_html
    assert "/static/portal/live-translate-studio.css" in subdub_html

    for public_route in ("/login", "/register", "/features"):
        html_out = app_mod._attach_live_translate_studio(copyfast_pages.render_portal(public_route), public_route).body.decode("utf-8")
        assert "/static/portal/live-translate-studio.js" not in html_out
        assert "/static/portal/live-translate-studio.css" not in html_out

    sw = (Path(__file__).resolve().parents[1] / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
    assert '"/static/portal/live-translate-studio.js"' in sw
    assert '"/static/portal/live-translate-studio.css"' in sw


def test_admin_admission_with_unreconciled_wallet_and_multiworker_ws_ingress(tmp_path, monkeypatch):
    db_file = tmp_path / "rt_admin_mw.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_file))
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_file))
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(db_file))
    monkeypatch.setenv("TOAN_AAS_ENV", "production")
    monkeypatch.setenv("REALTIME_STREAM_SECRET", "webapp-test-stream-secret-32-bytes")
    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "http://127.0.0.1:8080")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "test-bridge-token-32-bytes-minimum")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "test-hmac-secret-32-bytes-minimum")

    async def fake_bridge(method, path, payload=None, params=None, actor_id=None, **kwargs):
        if path == "/internal/v1/wallet":
            # Matches real VPS scenario where Bot wallet has snapshot_credits=500 but ledger_credits=200
            return {
                "ok": False,
                "status": "guarded",
                "error_code": "WALLET_LEDGER_UNRECONCILED",
                "message": "Phát hiện sai lệch đối soát giữa số dư ví và sổ cái giao dịch.",
                "data": {"balance_xu": 500},
            }
        return {"ok": False}

    monkeypatch.setattr(copyfast_bridge, "bridge_request", fake_bridge)

    class DummyReq:
        pass

    async def _run():
        req = rt.CreateSessionRequest(source_language="auto", target_language="vi", mode="LIVE_DUB_BILINGUAL")

        # 1. Admin with unreconciled wallet (500 Xu) MUST be admitted cleanly
        admin_acc = {"id": "web_admin_uuid", "role": "admin", "canonical_user_id": "7126457028"}
        created = await rt.create_live_translate_session(req, DummyReq(), account=admin_acc)
        assert created.ok is True
        sid = created.session_id
        token = created.stream_token

        # 2. Non-admin with WALLET_LEDGER_UNRECONCILED remains fail-closed with 402
        normal_acc = {"id": "web_user_uuid", "role": "user", "canonical_user_id": "999111222"}
        import pytest as _pytest
        with _pytest.raises(Exception) as exc:
            await rt.create_live_translate_session(req, DummyReq(), account=normal_acc)
        assert "402" in str(exc.value)

        # 3. Worker #2 receives WebSocket connection even when _ACTIVE_INGRESS_BUFFERS is empty in RAM
        rt._ACTIVE_SESSIONS.clear()
        rt._ACTIVE_INGRESS_BUFFERS.clear()
        rt._SESSION_CANONICAL_ACTORS.clear()

        class FakeWS:
            def __init__(self):
                self.accepted = False
                self.closed = False
                self.close_code = None
                self.sent = []
            async def accept(self):
                self.accepted = True
            async def close(self, code=1000, reason=""):
                self.closed = True
                self.close_code = code
            async def send_json(self, obj):
                self.sent.append(obj)
            async def receive(self):
                from fastapi import WebSocketDisconnect
                raise WebSocketDisconnect(code=1000)

        ws = FakeWS()
        await rt.websocket_live_stream(ws, sid, token=token)
        assert ws.accepted is True
        assert ws.close_code != 4404
        assert any(m.get("type") == "session.ready" for m in ws.sent)

    asyncio.run(_run())


def test_focus_live_mode_and_extension_admin_guards():
    root = Path(__file__).resolve().parents[1]
    studio_js = (root / "static" / "portal" / "live-translate-studio.js").read_text(encoding="utf-8")
    studio_css = (root / "static" / "portal" / "live-translate-studio.css").read_text(encoding="utf-8")
    popup_js = (root / "extensions" / "chrome-live-translate" / "popup.js").read_text(encoding="utf-8")
    content_js = (root / "extensions" / "chrome-live-translate" / "content.js").read_text(encoding="utf-8")
    content_css = (root / "extensions" / "chrome-live-translate" / "content.css").read_text(encoding="utf-8")
    offscreen_js = (root / "extensions" / "chrome-live-translate" / "offscreen.js").read_text(encoding="utf-8")
    assert "focus=live" in studio_js
    assert "portal-lt-focus-mode" in studio_css
    assert "_isAdminUser" in popup_js
    assert 'container.style.display = "none";' in content_js
    assert "bottom: 48px;" in content_css
    assert "nextTtsPlayTime" in offscreen_js and "activeTtsSources" in offscreen_js

    buf = rt.RealtimeAudioIngressBuffer()
    assert buf.max_segment_duration_ms <= 4000

    async def _check_exempt_status():
        sess = rt.RealtimeTranslateSession(
            "rts_exempt_check",
            rt.RealtimeSessionConfig(owner_id="web_admin", mode=rt.RealtimeTranslateMode.LIVE_DUB_BILINGUAL),
        )
        rt._SESSION_CANONICAL_ACTORS[sess.session_id] = "7126457028"
        rt._SESSION_UNBILLED_CHARS[sess.session_id] = 42
        rt._SESSION_BOT_BRIDGE_OK[sess.session_id] = 1
        orig_cfg = copyfast_bridge.CoreBridgeClient.configured
        orig_req = copyfast_bridge.bridge_request
        try:
            copyfast_bridge.CoreBridgeClient.configured = property(lambda self: True)
            async def fake_settle(*args, **kwargs):
                # Emulate _sanitize_envelope overwriting unknown 'exempt' status with 'failed'
                return {"ok": True, "status": "failed", "data": {"exempt": True, "amount_xu": 0, "balance_after": 500}}
            copyfast_bridge.bridge_request = fake_settle
            ev = await rt._settle_realtime_slice(sess, block_count=0, is_final=True)
            assert ev is not None and ev["status"] == "exempt"
        finally:
            copyfast_bridge.CoreBridgeClient.configured = orig_cfg
            copyfast_bridge.bridge_request = orig_req
    asyncio.run(_check_exempt_status())
