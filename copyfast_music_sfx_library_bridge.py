"""SFX Public Library Asset Search & Selection Bridge Adapter.

Task: WEBAPP_R36_BOT_AS_SOURCE_OF_TRUTH_FULL_FUNCTIONAL_PARITY_AND_GAP_CLOSURE_R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Product Family: MUSIC
Product: SFX_LIBRARY (Sound Effects Public Library)
Customer Entrypoint: /music/sfx-library
Web API Family: /api/v1/music/sfx-library/*

Connects the Web customer flow (/music/sfx-library) to a truthful mirror of the
Telegram Bot's canonical public SFX library capability:
- Bot Search: /sfx_library <query> -> freesound_search(query, limit=5)
- Bot Select: /select_sfx <number> -> select_media_preview("sfx", ...)
- Pricing & Xu: 0 Xu per search, 0 Xu per item selection (music_no_xu_text).
- Provider: Freesound public library asset search (NOT generative AI).
- Separation: Generative SFX (/music/sfx) is separate and remains a Web-only extension.

Invariants:
- Provider-Free Testing: When running in test environments (APP_ENV=test or
  WEBAPP_PROVIDER_CALLS_ENABLED!=true), returns deterministic mock library results
  without external network calls (0 provider network calls, 0 paid spend).
- Fail-Closed Admission: Empty query, invalid query, out-of-range index, and invalid
  asset IDs fail closed with HTTP 400.
- Owner Isolation: Search sessions and selection states are strictly scoped to account_id.
  Cross-account search session access and selection leakage are forbidden.
- Zero Wallet Impact: Search and selection operations are 0 Xu (cost_xu=0).
- Normalization: Normalized preview items match Bot schema: id, provider, title,
  author, duration, license, source_url, preview_url.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
import re
import sqlite3
from typing import Any
import uuid

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr, field_validator

from copyfast_db import ensure_copyfast_schema, read_transaction, transaction, utc_now


FREESOUND_SEARCH_ENDPOINT = "https://freesound.org/apiv2/search/text/"
FREESOUND_SEARCH_FIELDS = "id,name,username,duration,license,previews,url,tags"


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except Exception:
        return default


# Canonical pricing contracts mirroring Bot source (bot.py::calculate_music_price):
# Immediate charges on /sfx_library search and /select_sfx selection are 0 Xu ("Bot chưa trừ Xu")
SFX_LIBRARY_SEARCH_IMMEDIATE_CHARGE_XU = 0
SFX_LIBRARY_SELECT_IMMEDIATE_CHARGE_XU = 0

# Downstream consumption pricing when used in video rendering pipeline:
SFX_LIBRARY_XU_PER_ITEM = max(0, _env_int("SFX_LIBRARY_XU_PER_ITEM", 10))
SFX_LIBRARY_MIN_XU = max(0, _env_int("SFX_LIBRARY_MIN_XU", 10))
SFX_LIBRARY_USAGE_CHARGE_TRIGGER = "video_workflow_calculate_music_price"
SFX_LIBRARY_USAGE_PRICING_MODE = "sfx_library"

MAX_QUERY_LENGTH = 160
DEFAULT_SEARCH_LIMIT = 5
MAX_SEARCH_LIMIT = 5
MEDIA_PREVIEW_TTL_SECONDS = 3600.0

UNSAFE_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def ensure_sfx_library_schema(conn: sqlite3.Connection) -> None:
    """Ensure SQLite schema for SFX library searches and selections exists."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS web_sfx_library_searches (
            account_id TEXT PRIMARY KEY,
            query TEXT NOT NULL,
            results_json TEXT NOT NULL,
            callback_token TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(account_id) REFERENCES web_accounts(id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS web_sfx_library_selections (
            account_id TEXT PRIMARY KEY,
            asset_id TEXT NOT NULL,
            provider TEXT NOT NULL DEFAULT 'Freesound',
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            duration TEXT,
            license TEXT,
            preview_url TEXT,
            source_url TEXT,
            selected_at TEXT NOT NULL,
            FOREIGN KEY(account_id) REFERENCES web_accounts(id)
        )
        """
    )


def format_seconds(seconds: Any) -> str:
    """Format duration in seconds to MM:SS string matching Bot format_seconds."""
    if seconds is None:
        return "-"
    try:
        val = int(round(float(seconds)))
        m = val // 60
        s = val % 60
        return f"{m}:{s:02d}"
    except Exception:
        return "-"


def normalize_freesound_preview_item(item: dict) -> dict:
    """Normalize a raw Freesound item into canonical preview item schema."""
    previews = item.get("previews") or {}
    item_id = str(item.get("id") or "").strip()
    return {
        "id": item_id,
        "provider": "Freesound",
        "title": str(item.get("name") or "Untitled")[:120],
        "author": str(item.get("username") or "Unknown")[:100],
        "duration": format_seconds(item.get("duration")),
        "license": str(item.get("license") or "-")[:240],
        "source_url": str(item.get("url") or f"https://freesound.org/people/{item.get('username', 'user')}/sounds/{item_id}/").strip(),
        "preview_url": str(previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3") or f"https://cdn.freesound.org/previews/{item_id}.mp3").strip(),
    }


def _generate_mock_freesound_results(query: str, limit: int = 5) -> list[dict]:
    """Generate deterministic mock Freesound items for provider-free testing."""
    clean_query = query.strip().lower()
    results = []
    limit = max(1, min(limit, MAX_SEARCH_LIMIT))
    sample_tags = [clean_query, "sound", "effect", "audio", "production"]
    for i in range(1, limit + 1):
        asset_id = f"fs_{hashlib.sha256(f'{clean_query}_{i}'.encode()).hexdigest()[:8]}"
        results.append(
            {
                "id": asset_id,
                "name": f"{query.title()} Effect {i}",
                "username": f"sound_creator_{i}",
                "duration": 1.5 * i,
                "license": "Creative Commons Attribution 4.0",
                "url": f"https://freesound.org/sounds/{asset_id}/",
                "tags": sample_tags,
                "previews": {
                    "preview-hq-mp3": f"https://cdn.freesound.org/previews/{asset_id}_hq.mp3",
                    "preview-lq-mp3": f"https://cdn.freesound.org/previews/{asset_id}_lq.mp3",
                },
            }
        )
    return results


class SfxLibrarySearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: StrictStr
    limit: StrictInt | None = DEFAULT_SEARCH_LIMIT

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        s = str(v or "").strip()
        if not s:
            raise ValueError("Từ khóa tìm kiếm không được để trống")
        if len(s) > MAX_QUERY_LENGTH:
            raise ValueError(f"Từ khóa tìm kiếm tối đa {MAX_QUERY_LENGTH} ký tự")
        if UNSAFE_CONTROL_PATTERN.search(s):
            raise ValueError("Từ khóa tìm kiếm chứa ký tự không hợp lệ")
        return s

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int | None) -> int:
        if v is None:
            return DEFAULT_SEARCH_LIMIT
        if v < 1 or v > MAX_SEARCH_LIMIT:
            raise ValueError(f"Số lượng kết quả từ 1 đến {MAX_SEARCH_LIMIT}")
        return v


class SfxLibrarySelectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: StrictInt | None = None
    asset_id: StrictStr | None = None
    callback_token: StrictStr | None = None

    @field_validator("index")
    @classmethod
    def validate_index(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("Số thứ tự (index) phải lớn hơn hoặc bằng 1")
        return v


def search_sfx_library(
    account_id: str,
    query: str,
    limit: int = DEFAULT_SEARCH_LIMIT,
    mock_results: list[dict] | None = None,
    force_provider_error: bool = False,
) -> dict:
    """Execute public SFX library search, normalize items, and save search session."""
    clean_account = str(account_id or "").strip()
    if not clean_account:
        raise HTTPException(status_code=401, detail="Yêu cầu đăng nhập tài khoản")

    clean_query = str(query or "").strip()
    if not clean_query:
        raise HTTPException(status_code=400, detail="Từ khóa tìm kiếm không được để trống")
    if len(clean_query) > MAX_QUERY_LENGTH:
        raise HTTPException(status_code=400, detail=f"Từ khóa tìm kiếm tối đa {MAX_QUERY_LENGTH} ký tự")
    if UNSAFE_CONTROL_PATTERN.search(clean_query):
        raise HTTPException(status_code=400, detail="Từ khóa tìm kiếm chứa ký tự không hợp lệ")

    limit = max(1, min(limit, MAX_SEARCH_LIMIT))

    if force_provider_error:
        raise HTTPException(status_code=502, detail="Kho hiệu ứng âm thanh tạm thời không phản hồi. Chưa trừ Xu.")

    is_test_env = (
        os.environ.get("APP_ENV") == "test"
        or os.environ.get("WEBAPP_PROVIDER_CALLS_ENABLED", "false").lower() != "true"
    )

    if mock_results is not None:
        raw_items = mock_results
    elif is_test_env:
        raw_items = _generate_mock_freesound_results(clean_query, limit=limit)
    else:
        # Live execution path (only when explicitly enabled and credentials exist)
        api_key = (os.environ.get("FREESOUND_API_KEY") or "").strip()
        client_secret = (os.environ.get("FREESOUND_CLIENT_SECRET") or "").strip()
        if not (api_key or client_secret):
            # Graceful fallback when not configured, mirrors Bot behavior
            raw_items = []
        else:
            try:
                import urllib.parse
                import urllib.request
                params = urllib.parse.urlencode({
                    "query": clean_query,
                    "page_size": limit,
                    "fields": FREESOUND_SEARCH_FIELDS,
                    "token": api_key,
                })
                req = urllib.request.Request(
                    f"{FREESOUND_SEARCH_ENDPOINT}?{params}",
                    headers={"User-Agent": "TOAN-AAS-Web/1.0", "Authorization": f"Token {api_key}" if api_key else ""},
                )
                with urllib.request.urlopen(req, timeout=10.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    raw_items = data.get("results") or []
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"Lỗi kết nối thư viện Freesound: {str(e)[:100]}. Chưa trừ Xu.")

    normalized_items = [normalize_freesound_preview_item(item) for item in raw_items[:limit]]
    callback_token = uuid.uuid4().hex
    now_iso = utc_now()

    with transaction() as conn:
        ensure_sfx_library_schema(conn)
        conn.execute(
            """
            INSERT OR REPLACE INTO web_sfx_library_searches (
                account_id, query, results_json, callback_token, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (clean_account, clean_query, json.dumps(normalized_items), callback_token, now_iso),
        )

    return {
        "query": clean_query,
        "count": len(normalized_items),
        "results": normalized_items,
        "callback_token": callback_token,
        "provider": "Freesound",
        "xu_charged": 0,
        "pricing_model": "free_public_library",
    }


def select_sfx_library_item(
    account_id: str,
    index: int | None = None,
    asset_id: str | None = None,
    callback_token: str | None = None,
) -> dict:
    """Select an SFX item from the account's latest search session."""
    clean_account = str(account_id or "").strip()
    if not clean_account:
        raise HTTPException(status_code=401, detail="Yêu cầu đăng nhập tài khoản")

    with read_transaction() as conn:
        ensure_sfx_library_schema(conn)
        cur = conn.execute(
            "SELECT query, results_json, callback_token, created_at FROM web_sfx_library_searches WHERE account_id = ?",
            (clean_account,),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=400, detail="Chưa có kết quả tìm kiếm nào gần đây. Vui lòng tìm kiếm trước bằng /sfx_library.")

    saved_token = row[2]
    if callback_token and str(callback_token).strip() != saved_token:
        raise HTTPException(status_code=400, detail="Phiên tìm kiếm không hợp lệ hoặc đã hết hạn.")

    try:
        results = json.loads(row[1])
    except Exception:
        results = []

    if not results:
        raise HTTPException(status_code=400, detail="Danh sách tìm kiếm gần nhất trống. Vui lòng thử tìm từ khóa khác.")

    selected_item = None
    if index is not None:
        if index < 1 or index > len(results):
            raise HTTPException(
                status_code=400,
                detail=f"Số thứ tự không hợp lệ. Vui lòng chọn số từ 1 đến {len(results)} trong kết quả vừa tìm.",
            )
        selected_item = results[index - 1]
    elif asset_id:
        clean_asset_id = str(asset_id).strip()
        for item in results:
            if item.get("id") == clean_asset_id:
                selected_item = item
                break
        if not selected_item:
            raise HTTPException(
                status_code=400,
                detail="Mã hiệu ứng âm thanh không tìm thấy trong kết quả vừa tìm.",
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="Vui lòng cung cấp số thứ tự (index) hoặc mã hiệu ứng (asset_id) để chọn.",
        )

    now_iso = utc_now()

    with transaction() as conn:
        ensure_sfx_library_schema(conn)
        conn.execute(
            """
            INSERT OR REPLACE INTO web_sfx_library_selections (
                account_id, asset_id, provider, title, author, duration, license, preview_url, source_url, selected_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                clean_account,
                str(selected_item.get("id") or ""),
                str(selected_item.get("provider") or "Freesound"),
                str(selected_item.get("title") or "Untitled"),
                str(selected_item.get("author") or "Unknown"),
                str(selected_item.get("duration") or "-"),
                str(selected_item.get("license") or "-"),
                str(selected_item.get("preview_url") or ""),
                str(selected_item.get("source_url") or ""),
                now_iso,
            ),
        )

    return {
        "selected": selected_item,
        "xu_charged": SFX_LIBRARY_SELECT_IMMEDIATE_CHARGE_XU,
        "message": "Đã chọn hiệu ứng âm thanh từ thư viện Freesound thành công. Bot chưa trừ Xu ở bước chọn.",
        "selected_at": now_iso,
    }


def get_selected_sfx_library_item(account_id: str) -> dict | None:
    """Read the currently selected SFX item for the specified account."""
    clean_account = str(account_id or "").strip()
    if not clean_account:
        return None

    with read_transaction() as conn:
        ensure_sfx_library_schema(conn)
        cur = conn.execute(
            """
            SELECT asset_id, provider, title, author, duration, license, preview_url, source_url, selected_at
            FROM web_sfx_library_selections
            WHERE account_id = ?
            """,
            (clean_account,),
        )
        row = cur.fetchone()

    if not row:
        return None

    return {
        "id": row[0],
        "provider": row[1],
        "title": row[2],
        "author": row[3],
        "duration": row[4],
        "license": row[5],
        "preview_url": row[6],
        "source_url": row[7],
        "selected_at": row[8],
    }


def get_sfx_library_policy() -> dict:
    """Return immutable policy metadata for public SFX library capability."""
    return {
        "provider": "Freesound",
        "capability": "sfx_library",
        "customer_entrypoint": "/music/sfx-library",
        "api_endpoints": {
            "search": "/api/v1/music/sfx-library/search",
            "select": "/api/v1/music/sfx-library/select",
            "selected": "/api/v1/music/sfx-library/selected",
            "policy": "/api/v1/music/sfx-library/policy",
        },
        "search_immediate_charge_xu": SFX_LIBRARY_SEARCH_IMMEDIATE_CHARGE_XU,
        "select_immediate_charge_xu": SFX_LIBRARY_SELECT_IMMEDIATE_CHARGE_XU,
        "usage_pricing": {
            "mode": SFX_LIBRARY_USAGE_PRICING_MODE,
            "per_item_xu": SFX_LIBRARY_XU_PER_ITEM,
            "min_xu": SFX_LIBRARY_MIN_XU,
            "charge_trigger": SFX_LIBRARY_USAGE_CHARGE_TRIGGER,
        },
        "pricing": {
            "search_xu": SFX_LIBRARY_SEARCH_IMMEDIATE_CHARGE_XU,
            "select_xu": SFX_LIBRARY_SELECT_IMMEDIATE_CHARGE_XU,
            "usage_xu_per_item": SFX_LIBRARY_XU_PER_ITEM,
            "usage_min_xu": SFX_LIBRARY_MIN_XU,
            "charge_trigger": SFX_LIBRARY_USAGE_CHARGE_TRIGGER,
            "currency": "Xu",
        },
        "type": "public_library_search",
        "generative_ai": False,
        "bot_parity_source": "bot.py::cmd_sfx_library / cmd_select_sfx / calculate_music_price",
    }
