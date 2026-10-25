"""Jamendo Public Music Library Search, Selection, and Safe Preview Bridge.

Task: WEBAPP_R40_MUSIC_LIBRARY_JAMENDO_SEARCH_SELECT_PREVIEW_PARITY_R1
Product Family: MUSIC
Product: MUSIC_LIBRARY (Jamendo Public Music Library)
Customer Entrypoint: /music/library, /music-library
Web API Family: /api/v1/music/library/*, /api/v1/music-library/*

Connects the Web customer flow to the Telegram Bot canonical Jamendo music library capability:
- Bot Search: /music_library <query> -> fetch_jamendo_tracks(query, limit=8)
- Bot Select: /select_music <number> -> 1-based index selection into SELECTED_MUSIC
- Immediate Charges: 0 Xu per search, 0 Xu per selection ("Chưa trừ Xu").
- Downstream Usage Pricing: Stock music library is included in video rendering workflows (0 Xu).
- Provider: Jamendo public tracks API (NOT generative AI).
- Browser Authority: Browser cannot send raw provider track ID as canonical authority (1-based index required).
- Preview Safety: Strict whitelist (jamendo.com / jamendocdn.com), no private IP, no credential leakage, no unsafe redirects.
- Media Workspace Complement: Existing Web media workspace (/library-items) remains a WEB_NATIVE_COMPLEMENT.
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
import sqlite3
from typing import Any
import urllib.parse

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr, field_validator

from copyfast_db import ensure_copyfast_schema, read_transaction, transaction, utc_now


JAMENDO_SEARCH_IMMEDIATE_CHARGE_XU = 0
JAMENDO_SELECT_IMMEDIATE_CHARGE_XU = 0
JAMENDO_DOWNSTREAM_USAGE_XU = 0
JAMENDO_USAGE_PRICING_MODE = "stock_music_library"

MAX_QUERY_LENGTH = 160
DEFAULT_SEARCH_LIMIT = 8
MAX_SEARCH_LIMIT = 10
MEDIA_PREVIEW_TTL_SECONDS = 600.0

UNSAFE_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
JAMENDO_TRUSTED_DOMAINS = (
    "jamendo.com",
    "jamendocdn.com",
)


def ensure_music_library_schema(conn: sqlite3.Connection) -> None:
    """Ensure SQLite schema for Music Library searches and selections exists."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS web_music_library_searches (
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
        CREATE TABLE IF NOT EXISTS web_music_library_selections (
            account_id TEXT PRIMARY KEY,
            asset_id TEXT NOT NULL,
            provider TEXT NOT NULL DEFAULT 'Jamendo',
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


class MusicLibrarySearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: StrictStr
    limit: StrictInt | None = DEFAULT_SEARCH_LIMIT
    mock_results: list[dict] | None = None

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


class MusicLibrarySelectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: StrictInt | None = None
    track_id: StrictStr | None = None
    asset_id: StrictStr | None = None
    callback_token: StrictStr | None = None

    @field_validator("index")
    @classmethod
    def validate_index(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("Số thứ tự (index) phải lớn hơn hoặc bằng 1")
        return v


def is_safe_preview_url(url: str) -> bool:
    """Validate preview URL against trusted Jamendo CDN domains, blocking private IPs and unsafe schemes."""
    if not url or not isinstance(url, str):
        return False
    clean = url.strip()
    clean_lower = clean.lower()
    dangerous_schemes = ("javascript:", "data:", "file:", "vbscript:", "blob:")
    if any(clean_lower.startswith(sch) for sch in dangerous_schemes) or "<script" in clean_lower:
        return False
    if not (clean_lower.startswith("http://") or clean_lower.startswith("https://")):
        return False
    try:
        parsed = urllib.parse.urlparse(clean)
        hostname = (parsed.hostname or "").lower()
        if not hostname:
            return False
        if hostname in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
            return False
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
                return False
        except ValueError:
            pass
        return any(hostname == domain or hostname.endswith("." + domain) for domain in JAMENDO_TRUSTED_DOMAINS)
    except Exception:
        return False


def save_music_library_search(account_id: str, query: str, results: list[dict], callback_token: str) -> None:
    """Save account-isolated search session in SQLite."""
    clean_account = str(account_id or "").strip()
    if not clean_account:
        return
    now_iso = utc_now()
    with transaction() as conn:
        ensure_music_library_schema(conn)
        conn.execute(
            """
            INSERT OR REPLACE INTO web_music_library_searches (
                account_id, query, results_json, callback_token, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (clean_account, query, json.dumps(results), callback_token, now_iso),
        )


def save_music_library_selection(account_id: str, item: dict) -> None:
    """Save account-isolated selection in SQLite."""
    clean_account = str(account_id or "").strip()
    if not clean_account or not isinstance(item, dict):
        return
    now_iso = utc_now()
    asset_id = str(item.get("id") or "").strip()
    with transaction() as conn:
        ensure_music_library_schema(conn)
        conn.execute(
            """
            INSERT OR REPLACE INTO web_music_library_selections (
                account_id, asset_id, provider, title, author, duration, license, preview_url, source_url, selected_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                clean_account,
                asset_id,
                str(item.get("provider") or "Jamendo"),
                str(item.get("title") or "Untitled"),
                str(item.get("author") or "Unknown"),
                str(item.get("duration") or "-"),
                str(item.get("license") or "-"),
                str(item.get("preview_url") or ""),
                str(item.get("source_url") or ""),
                now_iso,
            ),
        )


def get_local_music_library_selection(account_id: str) -> dict | None:
    """Read account-scoped selection from SQLite."""
    clean_account = str(account_id or "").strip()
    if not clean_account:
        return None
    with read_transaction() as conn:
        ensure_music_library_schema(conn)
        cur = conn.execute(
            """
            SELECT asset_id, provider, title, author, duration, license, preview_url, source_url, selected_at
            FROM web_music_library_selections
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


def get_music_library_policy() -> dict:
    """Return canonical Jamendo music library pricing and capability policy."""
    return {
        "provider": "Jamendo",
        "search_immediate_cost_xu": JAMENDO_SEARCH_IMMEDIATE_CHARGE_XU,
        "select_immediate_cost_xu": JAMENDO_SELECT_IMMEDIATE_CHARGE_XU,
        "downstream_usage_pricing": {
            "mode": JAMENDO_USAGE_PRICING_MODE,
            "per_item_xu": JAMENDO_DOWNSTREAM_USAGE_XU,
            "min_xu": 0,
            "included": True,
        },
        "max_query_length": MAX_QUERY_LENGTH,
        "default_limit": DEFAULT_SEARCH_LIMIT,
        "max_limit": MAX_SEARCH_LIMIT,
        "session_ttl_seconds": int(MEDIA_PREVIEW_TTL_SECONDS),
        "selection_mode": "1_based_index",
        "raw_provider_track_id_authority": False,
        "preview_safety": "trusted_domains_only_no_redirect_no_private_ip",
        "pricing_terms": "search_and_select_immediate_free_downstream_stock_included",
    }
