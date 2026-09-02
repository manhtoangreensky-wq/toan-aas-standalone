"""Customer manual top-up payment instructions remain Web-local and truthful."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib
import json
import os
from pathlib import Path
import sqlite3
import shutil
import subprocess
from threading import Event

from fastapi.testclient import TestClient
from PIL import Image

from tests.test_copyfast_auth_api import make_client
from tests.test_web_manual_topup_unlinked_g1 import _register_and_login
from tests.test_web_manual_topup_unlinked_g2 import _admin


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")


def _configured_manual_env(monkeypatch, tmp_path: Path) -> Path:
    qr_path = tmp_path / "acb.png"
    Image.new("RGB", (32, 32), color=(16, 170, 150)).save(qr_path, format="PNG")
    values = {
        "MANUAL_BANK_CODE": "ACB",
        "MANUAL_BANK_NAME": "Asia Commercial Bank",
        "MANUAL_BANK_ACCOUNT": "0387532320",
        "MANUAL_BANK_OWNER": "TOAN AAS",
        "MANUAL_BANK_QR_PATH": str(qr_path),
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    return qr_path


def test_signed_options_and_qr_are_web_local_bounded_and_fail_closed(tmp_path, monkeypatch):
    qr_path = _configured_manual_env(monkeypatch, tmp_path)
    with make_client(tmp_path, monkeypatch) as client:
        assert client.get("/api/v1/payments/options/manual-methods/bank_acb_vietqr/qr").status_code == 401
        csrf = _register_and_login(client, "manual-qr@example.com")

        response = client.get("/api/v1/payments/options")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store, private"
        manual = response.json()["data"]["manual"]
        assert set(manual) == {
            "available", "payment_lookup_available", "wallet_history_signal_available",
            "history_in_web", "history_menu_label", "methods", "payment_destinations",
            "payment_code", "support_hotline",
        }
        assert all(set(item) == {"id", "label", "currency", "mode"} for item in manual["methods"])
        assert manual["payment_code"].isascii() and manual["payment_code"].isdigit()
        assert len(manual["payment_code"]) == 8
        assert manual["support_hotline"] == "0898360858"
        destination = manual["payment_destinations"]["bank_acb_vietqr"]
        assert destination == {
            "label": "ACB VietQR",
            "currency": "VND",
            "mode": "transfer",
            "display_ready": True,
            "request_enabled": True,
            "destination": {
                "bank_code": "ACB",
                "bank_name": "Asia Commercial Bank",
                "account_number": "0387532320",
                "account_owner": "TOAN AAS",
            },
            "qr_url": "/api/v1/payments/options/manual-methods/bank_acb_vietqr/qr",
        }
        serialized = json.dumps(manual, ensure_ascii=False)
        assert str(qr_path) not in serialized
        assert "MANUAL_BANK_QR_PATH" not in serialized

        qr = client.get(destination["qr_url"])
        assert qr.status_code == 200
        assert qr.headers["content-type"] == "image/png"
        assert qr.headers["cache-control"] == "no-store, private"
        assert qr.headers["cross-origin-resource-policy"] == "same-origin"
        assert qr.content.startswith(b"\x89PNG\r\n\x1a\n")

        monkeypatch.setenv("MANUAL_BANK_QR_PATH", str(tmp_path / "missing.png"))
        missing = client.get(destination["qr_url"])
        assert missing.status_code == 404
        assert missing.headers["cross-origin-resource-policy"] == "same-origin"
        unknown = client.get("/api/v1/payments/options/manual-methods/not-a-method/qr")
        assert unknown.status_code == 404
        assert unknown.headers["cross-origin-resource-policy"] == "same-origin"

        disabled = client.post(
            "/api/v1/payments/manual",
            headers={"X-CSRF-Token": csrf},
            json={
                "amount_vnd": 50_000,
                "method": "zalopay_personal",
                "reference": "DISABLED-METHOD",
                "idempotency_key": "manual-disabled-method-0001",
            },
        )
        assert disabled.status_code == 409
        assert disabled.json()["error_code"] == "MANUAL_TOPUP_METHOD_UNAVAILABLE"
        with sqlite3.connect(tmp_path / "copyfast-test.db") as conn:
            assert conn.execute("SELECT COUNT(*) FROM web_manual_topup_requests").fetchone()[0] == 0


def test_malformed_qr_is_not_published_or_served(tmp_path, monkeypatch):
    malformed = tmp_path / "momo.png"
    malformed.write_bytes(b"\x89PNG\r\n\x1a\nnot-a-decodable-image")
    monkeypatch.setenv("MANUAL_MOMO_TUITHANTAI_QR_PATH", str(malformed))
    with make_client(tmp_path, monkeypatch) as client:
        _register_and_login(client, "manual-malformed@example.com")
        manual = client.get("/api/v1/payments/options").json()["data"]["manual"]
        momo = manual["payment_destinations"]["momo_tuithantai"]
        assert momo["display_ready"] is False
        assert momo["request_enabled"] is False
        assert "qr_url" not in momo
        response = client.get("/api/v1/payments/options/manual-methods/momo_tuithantai/qr")
        assert response.status_code == 404
        assert response.headers["cross-origin-resource-policy"] == "same-origin"


def test_validated_qr_decode_is_cached_by_filesystem_identity(tmp_path, monkeypatch):
    qr_path = _configured_manual_env(monkeypatch, tmp_path)
    api = importlib.import_module("copyfast_api")
    api._validated_manual_qr_asset.cache_clear()
    first = api._manual_qr_asset("bank_acb_vietqr")
    after_first = api._validated_manual_qr_asset.cache_info()
    second = api._manual_qr_asset("bank_acb_vietqr")
    after_second = api._validated_manual_qr_asset.cache_info()
    assert first == second and first is not None
    assert after_second.hits == after_first.hits + 1
    assert after_second.misses == after_first.misses

    original_stat = qr_path.stat()
    Image.new("RGB", (33, 33), color=(20, 100, 200)).save(qr_path, format="PNG")
    os.utime(qr_path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns + 2_000_000_000))
    third = api._manual_qr_asset("bank_acb_vietqr")
    after_change = api._validated_manual_qr_asset.cache_info()
    assert third is not None and third[0] != first[0]
    assert after_change.misses == after_second.misses + 1


def test_decompression_bomb_qr_fails_closed_with_security_headers(tmp_path, monkeypatch):
    bomb = tmp_path / "momo.png"
    Image.new("RGB", (32, 32), color=(16, 170, 150)).save(bomb, format="PNG")
    monkeypatch.setenv("MANUAL_MOMO_TUITHANTAI_QR_PATH", str(bomb))
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1)
    with make_client(tmp_path, monkeypatch) as client:
        _register_and_login(client, "manual-bomb@example.com")
        options = client.get("/api/v1/payments/options")
        assert options.status_code == 200
        momo = options.json()["data"]["manual"]["payment_destinations"]["momo_tuithantai"]
        assert momo["display_ready"] is False
        assert momo["request_enabled"] is False
        assert "qr_url" not in momo
        response = client.get("/api/v1/payments/options/manual-methods/momo_tuithantai/qr")
        assert response.status_code == 404
        assert response.headers["cache-control"] == "no-store, private"
        assert response.headers["cross-origin-resource-policy"] == "same-origin"
        assert response.headers["x-content-type-options"] == "nosniff"


def test_web_private_asset_root_is_a_runtime_fallback_not_a_public_static_asset(tmp_path, monkeypatch):
    private_root = tmp_path / "web-private"
    private_root.mkdir()
    qr_path = private_root / "acb_vietqr_manual.jpg"
    Image.new("RGB", (32, 32), color=(16, 170, 150)).save(qr_path, format="JPEG")
    monkeypatch.delenv("MANUAL_BANK_QR_PATH", raising=False)
    for name in ("MANUAL_BANK_CODE", "MANUAL_BANK_NAME", "MANUAL_BANK_ACCOUNT", "MANUAL_BANK_OWNER"):
        monkeypatch.delenv(name, raising=False)
    (private_root / "config.json").write_text(json.dumps({
        "bank_code": "ACB",
        "bank_name": "Asia Commercial Bank",
        "bank_account": "0387532320",
        "bank_owner": "TOAN AAS",
    }), encoding="utf-8")
    with make_client(tmp_path, monkeypatch) as client:
        api = importlib.import_module("copyfast_api")
        monkeypatch.setattr(api, "MANUAL_TOPUP_PRIVATE_ASSET_DIR", private_root)
        _register_and_login(client, "manual-private-root@example.com")
        destination = client.get("/api/v1/payments/options").json()["data"]["manual"]["payment_destinations"]["bank_acb_vietqr"]
        assert destination["display_ready"] is True
        assert destination["request_enabled"] is True
        assert destination["destination"]["account_number"] == "0387532320"
        assert destination["qr_url"].startswith("/api/v1/payments/options/manual-methods/")
        assert str(private_root) not in json.dumps(destination)
        response = client.get(destination["qr_url"])
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        assert response.content == qr_path.read_bytes()


def test_acb_vietqr_requires_complete_destination_and_qr(tmp_path, monkeypatch):
    qr_path = tmp_path / "acb.png"
    Image.new("RGB", (32, 32), color=(16, 170, 150)).save(qr_path, format="PNG")
    monkeypatch.setenv("MANUAL_BANK_QR_PATH", str(qr_path))
    for name in ("MANUAL_BANK_CODE", "MANUAL_BANK_NAME", "MANUAL_BANK_ACCOUNT", "MANUAL_BANK_OWNER"):
        monkeypatch.delenv(name, raising=False)
    with make_client(tmp_path, monkeypatch) as client:
        csrf = _register_and_login(client, "manual-acb-partial@example.com")
        method = client.get("/api/v1/payments/options").json()["data"]["manual"]["payment_destinations"]["bank_acb_vietqr"]
        assert method["display_ready"] is False
        assert method["request_enabled"] is False
        assert "destination" not in method
        blocked = client.post(
            "/api/v1/payments/manual",
            headers={"X-CSRF-Token": csrf},
            json={
                "amount_vnd": 50_000,
                "method": "bank_acb_vietqr",
                "reference": "PARTIAL-ACB",
                "idempotency_key": "manual-partial-acb-0001",
            },
        )
        assert blocked.status_code == 409
        assert blocked.json()["error_code"] == "MANUAL_TOPUP_METHOD_UNAVAILABLE"
        with sqlite3.connect(tmp_path / "copyfast-test.db") as conn:
            assert conn.execute("SELECT COUNT(*) FROM web_manual_topup_requests").fetchone()[0] == 0


def test_unlinked_renderer_contract_shows_methods_qr_amount_code_without_bridge_copy():
    for marker in (
        "portal-manual-payment-methods",
        "data-manual-payment-method=",
        "payment_destinations",
        "name=\"amount_vnd\"",
        "manualTopupText(\"paymentCode\"",
    ):
        assert marker in PORTAL
    hydration = INTEGRATION[
        INTEGRATION.index('if (account && currentPath === "/wallet/topup") {'):
        INTEGRATION.index('if (account && currentPath === "/wallet/topup") {') + 240
    ]
    assert "hydratePaymentOptions" in hydration
    assert "telegramLinked" not in hydration
    assert "bridgeAvailable" not in hydration


def test_real_portal_renderer_outputs_ready_and_unavailable_cards_with_form():
    node = shutil.which("node")
    assert node, "Node.js is required for the real renderer contract"
    script = r'''
const fs = require("fs"), vm = require("vm");
const portal = fs.readFileSync(__PORTAL__, "utf8");
const i18n = fs.readFileSync(__I18N__, "utf8");
const cls=()=>({add(){},remove(){},toggle(){return false;},contains(){return false;}});
const el=(id="")=>({id,innerHTML:"",textContent:"",dataset:{},style:{},classList:cls(),children:[],hidden:false,disabled:false,setAttribute(){},getAttribute(){return "";},removeAttribute(){},hasAttribute(){return false;},querySelector(){return null;},querySelectorAll(){return[];},addEventListener(){},removeEventListener(){},appendChild(x){this.children.push(x);return x;},prepend(x){this.children.unshift(x);return x;},remove(){},focus(){},contains(){return false;}});
const sidebar=el("sidebar"),header=el("header"),main=el("main"),shell=el("shell"),mobile=el("mobile"),palette=el("palette"),body=el("body"),docEl=el("html");
const document = {
  readyState:"loading", body, documentElement:docEl, activeElement:null, createElement:()=>el(),
  addEventListener(){}, removeEventListener(){}, querySelectorAll(){return[];},
  querySelector(selector){ if(selector.includes("data-portal-sidebar"))return sidebar; if(selector.includes("data-portal-header"))return header; if(selector.includes("data-portal-main"))return main; if(selector.includes("data-portal-shell"))return shell; if(selector.includes("data-portal-mobile-nav"))return mobile; if(selector.includes("data-portal-command-palette"))return palette; return null; },
  getElementById(){return null;}
};
const storage=()=>({getItem(){return null;},setItem(){},removeItem(){}});
const window={__TOAN_AAS_PORTAL__:{},location:{pathname:"/wallet/topup",search:"",href:"http://test/wallet/topup"},history:{pushState(){},replaceState(){}},innerWidth:390,
 addEventListener(){},removeEventListener(){},dispatchEvent(){return true;},matchMedia(){return{matches:false,addEventListener(){},removeEventListener(){}}},
 setTimeout(){return 1;},clearTimeout(){},requestAnimationFrame(fn){fn();return 1;},cancelAnimationFrame(){},scrollTo(){},localStorage:storage(),sessionStorage:storage(),
 TOANAASPortalMotion:{replace(_s,_m,render){render();}}};
const context={console,process,window,document,navigator:{standalone:false,userAgent:"node"},URL,URLSearchParams,Intl,setTimeout:window.setTimeout,clearTimeout:window.clearTimeout,requestAnimationFrame:window.requestAnimationFrame,cancelAnimationFrame:window.cancelAnimationFrame,CustomEvent:function(){},Event:function(){},CSS:{escape:String}};
context.globalThis=context; vm.createContext(context); vm.runInContext(i18n+"\n"+portal,context);
const method=(id,label)=>({id,label,currency:"VND",mode:"transfer"});
window.TOANAASPortal.mount({path:"/wallet/topup",interfaceLocale:"vi",session:{authenticated:true,account:{id:"web-account"}},capabilities:{},wallet:null,
 paymentOptions:{payos:{request_enabled:false,topup_catalog_available:false,topup_packages:[]},manual:{available:true,history_in_web:true,payment_code:"10000000",support_hotline:"0898360858",methods:[method("bank_acb_vietqr","ACB VietQR"),method("momo_tuithantai","MoMo")],payment_destinations:{bank_acb_vietqr:{label:"ACB VietQR",currency:"VND",mode:"transfer",display_ready:true,request_enabled:true,qr_url:"/api/v1/payments/options/manual-methods/bank_acb_vietqr/qr"},momo_tuithantai:{label:"MoMo",currency:"VND",mode:"transfer",display_ready:false,request_enabled:false}}}},
 manualTopupFlow:{status:"form",data:{}},manualTopupHistory:[],manualTopupReadState:"ready"},{reason:"entry"});
const html=main.innerHTML;
for(const marker of ['data-manual-payment-method="bank_acb_vietqr"','data-manual-payment-ready="true"','data-manual-payment-method="momo_tuithantai"','data-manual-payment-ready="false"','name="amount_vnd"','10000000','0898360858','Chưa được cấu hình']) if(!html.includes(marker)) throw new Error("missing:"+marker+" html:"+html.slice(0,1600));
if(html.includes("Telegram")||html.includes("Core Bridge")) throw new Error("bridge copy leaked");
process.stdout.write(JSON.stringify({ok:true,length:html.length}));
'''.replace("__PORTAL__", json.dumps(str(ROOT / "static" / "portal" / "portal.js"))).replace("__I18N__", json.dumps(str(ROOT / "static" / "portal" / "portal-i18n.js")));
    result = subprocess.run([node, "-e", script], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["ok"] is True


def test_real_client_normalizer_derives_readiness_from_safe_fields():
    node = shutil.which("node")
    assert node, "Node.js is required for the real normalizer contract"
    source = INTEGRATION[
        INTEGRATION.index("const MANUAL_PAYMENT_METHOD_CURRENCIES"):
        INTEGRATION.index("async function hydratePaymentOptions")
    ]
    script = r'''
const vm=require("vm");
const context={}; vm.createContext(context); vm.runInContext(__SOURCE__,context);
const normalize=(value)=>vm.runInContext("safeManualPaymentOptions("+JSON.stringify(value)+")",context);
const method=(id,label,currency="VND")=>({id,label,currency,mode:"transfer"});
const malicious=normalize({available:true,history_in_web:true,payment_code:"10000000",support_hotline:"0898360858",methods:[method("zalopay_personal","ZaloPay")],payment_destinations:{zalopay_personal:{label:"ZaloPay",currency:"VND",mode:"transfer",display_ready:true,request_enabled:true,qr_url:"https://evil.example/qr"}}});
if(malicious.payment_destinations.zalopay_personal.display_ready!==false||malicious.payment_destinations.zalopay_personal.request_enabled!==false||malicious.payment_destinations.zalopay_personal.qr_url) throw new Error("malicious readiness survived");
const valid=normalize({available:true,history_in_web:true,payment_code:"10000000",support_hotline:"0898360858",methods:[method("zalopay_personal","ZaloPay")],payment_destinations:{zalopay_personal:{label:"ZaloPay",currency:"VND",mode:"transfer",display_ready:true,request_enabled:true,qr_url:"/api/v1/payments/options/manual-methods/zalopay_personal/qr"}}});
if(valid.payment_destinations.zalopay_personal.display_ready!==true||valid.payment_destinations.zalopay_personal.request_enabled!==true) throw new Error("valid readiness lost");
process.stdout.write(JSON.stringify({ok:true}));
'''.replace("__SOURCE__", json.dumps(source));
    result = subprocess.run([node, "-e", script], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["ok"] is True


def test_configured_vnd_request_is_pending_and_visible_to_web_admin(tmp_path, monkeypatch):
    database_path = tmp_path / "manual-visible-admin.db"
    _configured_manual_env(monkeypatch, tmp_path)
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ADMIN_WRITES_ENABLED", "true")

    with make_client(tmp_path, monkeypatch, session_database_path=database_path) as customer:
        csrf = _register_and_login(customer, "manual-visible-customer@example.com")
        api = importlib.import_module("copyfast_api")

        def forbidden_call(*_args, **_kwargs):
            raise AssertionError("manual Web-local pending flow must not call bridge/provider/PayOS/Telegram")

        monkeypatch.setattr(api, "bridge_request", forbidden_call)
        monkeypatch.setattr(api, "_manual_topup_bridge", forbidden_call)
        monkeypatch.setattr(api, "manual_admin_bridge_request", forbidden_call)
        manual = customer.get("/api/v1/payments/options").json()["data"]["manual"]
        method = "bank_acb_vietqr"
        assert manual["payment_destinations"][method]["request_enabled"] is True
        created = customer.post(
            "/api/v1/payments/manual",
            headers={"X-CSRF-Token": csrf},
            json={
                "amount_vnd": 125_000,
                "method": method,
                "reference": "TX-WEB-125",
                "idempotency_key": "manual-visible-admin-0001",
            },
        )
        replay = customer.post(
            "/api/v1/payments/manual",
            headers={"X-CSRF-Token": csrf},
            json={
                "amount_vnd": 125_000,
                "method": method,
                "reference": "TX-WEB-125",
                "idempotency_key": "manual-visible-admin-0001",
            },
        )
        assert created.status_code == replay.status_code == 200
        record = created.json()["data"]
        replay_record = replay.json()["data"]
        assert replay_record.pop("idempotent_replay") is True
        assert replay_record == record
        assert record["status"] == "pending_admin_review"
        assert record["transfer_content"] == manual["payment_code"]
        assert "expected_xu" not in record and "approved_xu" not in record
        monkeypatch.setenv("MANUAL_BANK_QR_PATH", str(tmp_path / "now-missing.png"))
        replay_after_config_loss = customer.post(
            "/api/v1/payments/manual",
            headers={"X-CSRF-Token": csrf},
            json={
                "amount_vnd": 125_000,
                "method": method,
                "reference": "TX-WEB-125",
                "idempotency_key": "manual-visible-admin-0001",
            },
        )
        assert replay_after_config_loss.status_code == 200
        assert replay_after_config_loss.json()["data"]["idempotent_replay"] is True
        with sqlite3.connect(database_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM web_manual_topup_requests").fetchone()[0] == 1

    with TestClient(importlib.import_module("app").app) as admin:
        _admin(admin, database_path, "manual-visible-admin@example.com")
        listed = admin.get("/api/v1/admin/payments/manual?status=pending&limit=20")
        assert listed.status_code == 200
        rows = listed.json()["data"]["items"]
        row = next(item for item in rows if item["request_id"] == record["request_id"])
        assert row["email"] == "manual-visible-customer@example.com"
        assert row["amount_vnd"] == 125_000
        assert row["method"] == method
        assert row["payment_code"] == manual["payment_code"]
        assert "expected_xu" not in row and "approved_xu" not in row
        detail = admin.get(f"/api/v1/admin/payments/manual/{record['request_id']}")
        assert detail.status_code == 200
        assert detail.json()["data"] == row


def test_atomic_admission_preserves_concurrent_same_key_replay(tmp_path, monkeypatch):
    database_path = tmp_path / "atomic-admission.db"
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(database_path))
    db = importlib.import_module("copyfast_db")
    db.ensure_copyfast_schema()
    account_id = "atomic-admission-account"
    now = db.utc_now()
    with db.transaction() as conn:
        conn.execute(
            """INSERT INTO web_accounts
               (id, email, password_hash, display_name, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (account_id, "atomic@example.com", "hash", "Atomic", now, now),
        )

    key_hash = hashlib.sha256(b"atomic-admission-key-0001").hexdigest()
    fingerprint = hashlib.sha256(b"atomic-admission-fingerprint").hexdigest()
    admission_started = Event()
    release_admission = Event()

    def first_admission() -> bool:
        admission_started.set()
        assert release_admission.wait(timeout=10)
        return True

    def create_first() -> dict:
        return db.create_web_manual_topup_request(
            account_id=account_id,
            amount_vnd=125_000,
            method="bank_acb_vietqr",
            reference="ATOMIC",
            idempotency_key_hash=key_hash,
            request_fingerprint=fingerprint,
            admission_check=first_admission,
        )

    def create_replay() -> dict:
        return db.create_web_manual_topup_request(
            account_id=account_id,
            amount_vnd=125_000,
            method="bank_acb_vietqr",
            reference="ATOMIC",
            idempotency_key_hash=key_hash,
            request_fingerprint=fingerprint,
            admission_check=lambda: False,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(create_first)
        assert admission_started.wait(timeout=10)
        replay = pool.submit(create_replay)
        release_admission.set()
        records = [first.result(timeout=20), replay.result(timeout=20)]

    assert records[0]["request_id"] == records[1]["request_id"]
    assert sum(record.get("idempotent_replay") is True for record in records) == 1
    with sqlite3.connect(database_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM web_manual_topup_requests").fetchone()[0] == 1
