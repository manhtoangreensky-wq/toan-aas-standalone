"""Focused contracts for the redacted Web-native Admin customer directory."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import copyfast_admin_customer_directory as directory


ROOT = Path(__file__).resolve().parents[1]
ALPHA_ID = "00000000-0000-4000-8000-000000000001"
TELEGRAM_ID = "00000000-0000-4000-8000-000000000002"
OAUTH_ID = "00000000-0000-4000-8000-000000000003"
BETA_ID = "00000000-0000-4000-8000-000000000004"
GAMMA_ID = "00000000-0000-4000-8000-000000000005"
TELEGRAM_ALIAS = "telegram-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@telegram.toanaas.invalid"
OAUTH_ALIAS = "oauth-google-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@oauth.toanaas.invalid"


def _database() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute(
        """CREATE TABLE web_accounts (
            id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL DEFAULT '', canonical_user_id TEXT UNIQUE,
            role_cache TEXT NOT NULL DEFAULT 'user', is_active INTEGER NOT NULL DEFAULT 1,
            password_login_enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE web_account_profiles (
            account_id TEXT PRIMARY KEY, locale TEXT NOT NULL DEFAULT 'vi',
            timezone TEXT NOT NULL DEFAULT 'Asia/Ho_Chi_Minh',
            avatar_style TEXT NOT NULL DEFAULT 'gradient',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )"""
    )
    conn.executemany(
        """INSERT INTO web_accounts
           (id, email, password_hash, display_name, canonical_user_id, role_cache,
            is_active, password_login_enabled, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (ALPHA_ID, "alpha@example.com", "password-alpha-secret", "Alpha 100% Studio", None, "user", 1, 1, "2026-01-05T00:00:00Z", "2026-01-05T01:00:00Z"),
            (TELEGRAM_ID, TELEGRAM_ALIAS, "password-telegram-secret", "Khách Telegram", "telegram-canonical-secret", "admin", 0, 0, "2026-01-04T00:00:00Z", "2026-01-04T01:00:00Z"),
            (OAUTH_ID, OAUTH_ALIAS, "password-oauth-secret", "Khách OAuth", None, "support_operator", 1, 0, "2026-01-03T00:00:00Z", "2026-01-03T01:00:00Z"),
            (BETA_ID, "beta@example.com", "password-beta-secret", "Beta_Studio", None, "support_manager", 1, 1, "2026-01-02T00:00:00Z", "2026-01-02T01:00:00Z"),
            (GAMMA_ID, "gamma@example.com", "password-gamma-secret", "Gamma", None, "unexpected_role", 1, 1, "2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"),
        ],
    )
    conn.executemany(
        """INSERT INTO web_account_profiles
           (account_id, locale, timezone, avatar_style, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [
            (ALPHA_ID, "en", "UTC", "solid", "2026-01-05T00:00:00Z", "2026-01-05T01:00:00Z"),
            (TELEGRAM_ID, "vi", "Asia/Ho_Chi_Minh", "gradient", "2026-01-04T00:00:00Z", "2026-01-04T01:00:00Z"),
        ],
    )
    conn.commit()
    return conn


def _client(conn: sqlite3.Connection, *, actor: str = "admin") -> TestClient:
    app = FastAPI()
    app.include_router(directory.router)

    @contextmanager
    def read_transaction():
        yield conn

    def guard() -> dict[str, str]:
        if actor == "anonymous":
            raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để tiếp tục")
        if actor != "admin":
            raise HTTPException(status_code=403, detail="Chỉ quản trị viên được phép truy cập")
        return {"id": "admin-account", "role": "admin"}

    directory.read_transaction = read_transaction
    app.dependency_overrides[directory.require_admin] = guard
    return TestClient(app)


def _snapshot(conn: sqlite3.Connection) -> tuple[list[tuple], list[tuple]]:
    accounts = conn.execute("SELECT * FROM web_accounts ORDER BY id").fetchall()
    profiles = conn.execute("SELECT * FROM web_account_profiles ORDER BY account_id").fetchall()
    return accounts, profiles


def test_customer_directory_requires_signed_web_admin() -> None:
    conn = _database()
    for actor, expected_status in (("anonymous", 401), ("user", 403)):
        with _client(conn, actor=actor) as client:
            response = client.get("/api/v1/admin/customers")
        assert response.status_code == expected_status


def test_customer_list_is_bounded_filtered_and_has_exact_projection() -> None:
    conn = _database()
    with _client(conn) as client:
        response = client.get("/api/v1/admin/customers", params={"status": "active", "limit": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["status"] == "read_only"
    assert body["data"]["returned"] == 2
    assert body["data"]["has_more"] is True
    assert body["data"]["next_offset"] == 2
    assert body["data"]["filters"] == {"q": "", "status": "active"}
    customers = body["data"]["customers"]
    assert [item["id"] for item in customers] == [ALPHA_ID, OAUTH_ID]
    assert set(customers[0]) == {
        "id", "display_name", "email", "account_type", "role", "role_label",
        "status", "password_login_enabled", "telegram_linked", "profile",
        "created_at", "updated_at",
    }
    assert customers[0]["profile"] == {"locale": "en", "timezone": "UTC", "avatar_style": "solid"}


def test_search_treats_wildcards_as_literals_and_never_searches_internal_aliases() -> None:
    conn = _database()
    with _client(conn) as client:
        percent = client.get("/api/v1/admin/customers", params={"q": "%"}).json()["data"]["customers"]
        underscore = client.get("/api/v1/admin/customers", params={"q": "_"}).json()["data"]["customers"]
        backslash = client.get("/api/v1/admin/customers", params={"q": "\\"}).json()["data"]["customers"]
        internal = client.get("/api/v1/admin/customers", params={"q": "toanaas.invalid"}).json()["data"]["customers"]
        injection = client.get("/api/v1/admin/customers", params={"q": "' OR 1=1--"}).json()["data"]["customers"]
    assert [item["id"] for item in percent] == [ALPHA_ID]
    assert [item["id"] for item in underscore] == [BETA_ID]
    assert backslash == []
    assert internal == []
    assert injection == []


def test_pagination_is_stable_without_duplicate_accounts() -> None:
    conn = _database()
    with _client(conn) as client:
        pages = [
            client.get("/api/v1/admin/customers", params={"limit": 2, "offset": offset}).json()["data"]
            for offset in (0, 2, 4)
        ]
    ids = [item["id"] for page in pages for item in page["customers"]]
    assert ids == [ALPHA_ID, TELEGRAM_ID, OAUTH_ID, BETA_ID, GAMMA_ID]
    assert len(ids) == len(set(ids))
    assert [(page["has_more"], page["next_offset"]) for page in pages] == [(True, 2), (True, 4), (False, None)]


def test_detail_redacts_internal_identity_and_sensitive_storage() -> None:
    conn = _database()
    before = _snapshot(conn)
    with _client(conn) as client:
        telegram = client.get(f"/api/v1/admin/customers/{TELEGRAM_ID}")
        oauth = client.get(f"/api/v1/admin/customers/{OAUTH_ID}")
        all_rows = client.get("/api/v1/admin/customers", params={"limit": 100})
    assert telegram.status_code == 200
    telegram_customer = telegram.json()["data"]["customer"]
    assert telegram_customer["email"] == ""
    assert telegram_customer["account_type"] == "telegram"
    assert telegram_customer["telegram_linked"] is True
    assert telegram_customer["status"] == "locked"
    assert oauth.json()["data"]["customer"]["email"] == ""
    assert oauth.json()["data"]["customer"]["account_type"] == "oauth_only"
    rendered = telegram.text + oauth.text + all_rows.text
    for private in (
        TELEGRAM_ALIAS, OAUTH_ALIAS, "telegram-canonical-secret",
        "password-alpha-secret", "password-telegram-secret", "password-oauth-secret",
        "password-beta-secret", "password-gamma-secret", "canonical_user_id",
        "password_hash", "csrf", "session", "provider_token", "payos", "wallet",
    ):
        assert private not in rendered.lower()
    assert _snapshot(conn) == before


def test_invalid_filters_ids_and_missing_customer_fail_closed() -> None:
    conn = _database()
    missing_id = "00000000-0000-4000-8000-000000000099"
    with _client(conn) as client:
        assert client.get("/api/v1/admin/customers", params={"status": "deleted"}).status_code == 422
        assert client.get("/api/v1/admin/customers", params={"limit": 101}).status_code == 422
        assert client.get("/api/v1/admin/customers", params={"offset": 10001}).status_code == 422
        assert client.get("/api/v1/admin/customers/not-a-uuid").status_code == 422
        missing = client.get(f"/api/v1/admin/customers/{missing_id}")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Không tìm thấy tài khoản khách hàng"


def test_role_values_are_allowlisted() -> None:
    conn = _database()
    with _client(conn) as client:
        gamma = client.get(f"/api/v1/admin/customers/{GAMMA_ID}").json()["data"]["customer"]
    assert gamma["role"] == "other"
    assert gamma["role_label"] == "Vai trò khác"


def test_router_mounts_once_and_bot_admin_users_route_is_unchanged() -> None:
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    api_source = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
    assert app_source.count("import copyfast_admin_customer_directory") == 1
    assert app_source.count("app.include_router(copyfast_admin_customer_directory.router)") == 1
    protected_route = '''@router.get("/admin/users")
async def admin_users(request: Request, account: dict = Depends(require_canonical_admin)):
    return await _bridge("GET", "/internal/v1/admin/users", account=account, request=request, admin_read=True)'''
    assert protected_route in api_source
