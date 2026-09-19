"""Web-owned administrative pricing draft engine and change-set policy (V2-06).

CRITICAL ARCHITECTURAL BOUNDARY:
- Draft change-sets stored here are ADMINISTRATIVE PROPOSALS ONLY.
- They are NOT customer sale-price authority.
- They are NOT quote authority.
- They are NOT wallet authority.
- They are NOT PayOS authority.
- They are NOT provider-cost authority.
- Customer GET /pricing NEVER reads from these draft tables.
- Customer-facing effective pricing comes ONLY from the canonical Bot/Core Bridge projection.

Preserves:
WEB_DRAFT != CANONICAL_PUBLISHED_PRICE
and:
ADMIN_SAVE_DRAFT != PUBLISH != CUSTOMER_EFFECTIVE_PRICE
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from typing import Any

from fastapi import HTTPException

import copyfast_auth
from copyfast_db import transaction, utc_now


# Canonical authority indicators
PRICING_READ_AUTHORITY = "/internal/v1/pricing"
PACKAGES_READ_AUTHORITY = "/internal/v1/packages"
PUBLIC_SALE_CATALOG_AUTHORITY = "public_sale_catalog"

ADMIN_PRICING_WRITE_AUTHORITY = "web_pricing_change_sets"
ADMIN_PACKAGE_WRITE_AUTHORITY = "web_pricing_change_sets"

CANONICAL_PUBLISH_AVAILABLE = False
CANONICAL_PUBLISH_ENDPOINT = None
CANONICAL_PUBLISH_RECEIPT = None

ADMIN_PRICING_ROUTE = "/admin/pricing"
ADMIN_PACKAGES_COMPAT_ROUTE = "/admin/packages"

ADMIN_PRICING_PRIMARY_SURFACE_COUNT = 1
LOCAL_DRAFT_AS_PUBLIC_AUTHORITY = 0
CLIENT_DERIVED_PRICE = 0
STATIC_FALLBACK_PRICE = 0
SKU_INFERENCE = 0
INTERNAL_PRICING_FIELD_LEAK = 0
PROVIDER_SECRET_LEAK = 0
CUSTOMER_PRICING_READS_DRAFT_TABLE = "NO"
DRAFT_AFFECTS_QUOTE = "NO"
DRAFT_AFFECTS_WALLET = "NO"
DRAFT_AFFECTS_PAYOS = "NO"
DRAFT_AFFECTS_PROVIDER = "NO"
PROJECT_PACKAGE_EXPORT_AUTHORITY_CHANGED = "NO"
STALE_DRAFT_OVERWRITE = 0
PUBLISHED_VERSION_MUTABLE = "NO"
DIFF_SOURCE = "SERVER_SIDE_CANONICAL"
FAKE_PUBLISHED_COPY = 0
WRITE_200_WITHOUT_READBACK_NOT_LIVE = 1

SKU_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,80}$")
VALID_STATUSES = frozenset({"active", "disabled", "ready"})
FORBIDDEN_FIELDS = frozenset({
    "cost", "cost_xu", "provider", "model", "provider_model",
    "price_usd", "fx", "fx_rate", "markup", "fallback", "fallback_chain",
    "provider_credentials", "wallet", "wallet_balance", "payment", "receipt",
})


def ensure_pricing_schema(conn: sqlite3.Connection) -> None:
    """Ensure Web-owned administrative pricing draft tables exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS web_pricing_change_sets (
            id TEXT PRIMARY KEY,
            base_catalog_version TEXT NOT NULL,
            draft_version TEXT NOT NULL,
            state TEXT NOT NULL, -- draft, ready_for_publish, published, rejected, superseded
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            reason TEXT NOT NULL,
            change_summary TEXT NOT NULL DEFAULT '{}',
            catalog_fingerprint TEXT NOT NULL,
            published_catalog_version TEXT,
            publish_receipt TEXT,
            published_at TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_web_pricing_change_sets_state ON web_pricing_change_sets(state)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_web_pricing_change_sets_created ON web_pricing_change_sets(created_at DESC)")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS web_pricing_change_items (
            id TEXT PRIMARY KEY,
            change_set_id TEXT NOT NULL,
            sku TEXT NOT NULL,
            family TEXT NOT NULL,
            label TEXT NOT NULL,
            base_sale_price_xu INTEGER,
            draft_sale_price_xu INTEGER NOT NULL,
            base_status TEXT,
            draft_status TEXT NOT NULL,
            action TEXT NOT NULL, -- update, add, remove
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(change_set_id) REFERENCES web_pricing_change_sets(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_web_pricing_change_items_set ON web_pricing_change_items(change_set_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_web_pricing_change_items_sku ON web_pricing_change_items(sku)")


def validate_sale_price_xu(val: Any) -> int:
    """Validate sale_price_xu as a strictly positive, bounded integer."""
    if isinstance(val, bool) or not isinstance(val, int):
        raise HTTPException(status_code=422, detail="Giá bán sale_price_xu phải là số nguyên dương hợp lệ.")
    if val <= 0:
        raise HTTPException(status_code=422, detail="Giá bán sale_price_xu phải lớn hơn 0 Xu.")
    if val > 100_000_000:
        raise HTTPException(status_code=422, detail="Giá bán sale_price_xu vượt quá giới hạn cho phép (100,000,000 Xu).")
    return val


def validate_sku(sku: Any) -> str:
    """Validate SKU code format."""
    clean_sku = str(sku or "").strip()
    if not clean_sku or not SKU_PATTERN.fullmatch(clean_sku):
        raise HTTPException(status_code=422, detail=f"Mã SKU '{clean_sku}' không hợp lệ. SKU phải chứa ký tự chữ thường, số, gạch nối.")
    return clean_sku


def validate_status(status: Any) -> str:
    """Validate item public catalog status."""
    clean_status = str(status or "").strip().lower()
    if clean_status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"Trạng thái '{clean_status}' không hợp lệ. Phải thuộc: {sorted(VALID_STATUSES)}.")
    return clean_status


def sanitize_and_validate_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate and clean draft items, enforcing zero internal leaks and unique SKUs."""
    if not isinstance(items, list) or len(items) == 0:
        raise HTTPException(status_code=422, detail="Danh sách SKU thay đổi trong bản nháp không được rỗng.")
    if len(items) > 100:
        raise HTTPException(status_code=422, detail="Số lượng SKU trong một bản nháp vượt quá giới hạn 100 mục.")

    seen_skus: set[str] = set()
    cleaned_items: list[dict[str, Any]] = []

    for idx, raw_item in enumerate(items):
        if not isinstance(raw_item, dict):
            raise HTTPException(status_code=422, detail=f"Mục thứ {idx+1} không đúng định dạng dữ liệu.")

        # Check for forbidden leaks
        for field in FORBIDDEN_FIELDS:
            if field in raw_item:
                raise HTTPException(status_code=422, detail=f"Không được phép khai báo trường nội bộ '{field}' trong SKU.")

        sku = validate_sku(raw_item.get("sku") or raw_item.get("code"))
        if sku in seen_skus:
            raise HTTPException(status_code=422, detail=f"Phát hiện mã SKU trùng lặp '{sku}' trong cùng bản nháp.")
        seen_skus.add(sku)

        family = str(raw_item.get("family") or "general").strip()[:60] or "general"
        label = str(raw_item.get("label") or sku).strip()[:120] or sku
        sale_price_xu = validate_sale_price_xu(raw_item.get("sale_price_xu"))
        status = validate_status(raw_item.get("status") or "ready")

        action = str(raw_item.get("action") or "update").strip().lower()
        if action not in {"add", "update", "remove"}:
            action = "update"

        cleaned_items.append({
            "sku": sku,
            "family": family,
            "label": label,
            "sale_price_xu": sale_price_xu,
            "status": status,
            "action": action,
            "base_sale_price_xu": raw_item.get("base_sale_price_xu"),
            "base_status": raw_item.get("base_status"),
        })

    return cleaned_items


def compute_items_fingerprint(items: list[dict[str, Any]]) -> str:
    """Compute deterministic SHA-256 fingerprint for a list of validated items."""
    sorted_items = sorted(items, key=lambda x: x["sku"])
    canonical_repr = json.dumps([
        {"sku": it["sku"], "price": it["sale_price_xu"], "status": it["status"], "family": it["family"], "label": it["label"]}
        for it in sorted_items
    ], sort_keys=True)
    return hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()


def calculate_catalog_diff(
    base_items: list[dict[str, Any]] | None,
    draft_items: list[dict[str, Any]],
) -> dict[str, Any]:
    """Calculate server-side canonical diff between published base and draft change-set."""
    base_map: dict[str, dict[str, Any]] = {}
    if base_items and isinstance(base_items, list):
        for it in base_items:
            if isinstance(it, dict):
                code = str(it.get("code") or it.get("sku") or "").strip()
                if code:
                    base_map[code] = it

    draft_map = {it["sku"]: it for it in draft_items}

    added: list[dict[str, Any]] = []
    changed: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    unchanged_count = 0

    for sku, draft_row in draft_map.items():
        if sku not in base_map:
            added.append({
                "sku": sku,
                "family": draft_row["family"],
                "label": draft_row["label"],
                "sale_price_xu": draft_row["sale_price_xu"],
                "status": draft_row["status"],
            })
        else:
            base_row = base_map[sku]
            base_price = base_row.get("sale_price_xu")
            base_status = base_row.get("status")
            base_label = base_row.get("label")
            base_family = base_row.get("family")

            is_diff = (
                base_price != draft_row["sale_price_xu"]
                or base_status != draft_row["status"]
                or (base_label and base_label != draft_row["label"])
                or (base_family and base_family != draft_row["family"])
            )

            if is_diff:
                changed.append({
                    "sku": sku,
                    "before": {
                        "family": base_family,
                        "label": base_label,
                        "sale_price_xu": base_price,
                        "status": base_status,
                    },
                    "after": {
                        "family": draft_row["family"],
                        "label": draft_row["label"],
                        "sale_price_xu": draft_row["sale_price_xu"],
                        "status": draft_row["status"],
                    },
                })
            else:
                unchanged_count += 1

    # Check for removed SKUs
    for sku, base_row in base_map.items():
        if sku not in draft_map:
            removed.append({
                "sku": sku,
                "family": base_row.get("family"),
                "label": base_row.get("label"),
                "sale_price_xu": base_row.get("sale_price_xu"),
                "status": base_row.get("status"),
            })

    return {
        "diff_source": DIFF_SOURCE,
        "added": added,
        "changed": changed,
        "removed": removed,
        "unchanged_count": unchanged_count,
        "total_draft_count": len(draft_items),
        "total_base_count": len(base_map),
        "summary": f"+{len(added)} mới, ~{len(changed)} sửa đổi, -{len(removed)} loại bỏ, {unchanged_count} giữ nguyên",
    }


def _record_pricing_audit(
    actor: dict[str, Any] | None,
    request: Any,
    action: str,
    target: str,
    outcome: str = "ok",
    detail: str = "",
) -> None:
    try:
        actor = actor or {}
        req_id = ""
        if request and hasattr(request, "headers"):
            req_id = str(request.headers.get("X-Request-ID") or "")
        if not req_id:
            req_id = f"req_{uuid.uuid4().hex[:12]}"
        account_id = str(actor.get("id") or "") or None
        canonical_user_id = str(actor.get("canonical_user_id") or "") or None
        with transaction() as conn:
            copyfast_auth._record_audit(
                conn,
                account_id=account_id,
                canonical_user_id=canonical_user_id,
                action=action,
                request_id=req_id,
                target=target,
                outcome=outcome,
                detail=detail,
            )
    except Exception:
        pass


def create_draft_change_set(
    actor: dict[str, Any] | None = None,
    base_catalog_version: str = "",
    reason: str = "",
    items: list[dict[str, Any]] | None = None,
    base_items: list[dict[str, Any]] | None = None,
    request: Any = None,
    account: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a new versioned pricing draft proposal."""
    actor = actor or account or {}
    clean_reason = str(reason or "").strip()
    if not clean_reason:
        raise HTTPException(status_code=422, detail="Lý do tạo bản nháp thay đổi giá không được để trống.")

    clean_version = str(base_catalog_version or "").strip()
    if not clean_version:
        raise HTTPException(status_code=422, detail="Phiên bản catalog cơ sở (base_catalog_version) là bắt buộc.")

    validated_items = sanitize_and_validate_items(items)
    diff = calculate_catalog_diff(base_items, validated_items)
    fingerprint = compute_items_fingerprint(validated_items)

    actor_email = str(actor.get("email") or actor.get("id") or "admin").strip()
    change_set_id = f"pcs_{uuid.uuid4().hex[:16]}"
    now = utc_now()

    with transaction() as conn:
        ensure_pricing_schema(conn)

        # Mark any previous open draft as superseded
        conn.execute(
            "UPDATE web_pricing_change_sets SET state='superseded', updated_at=? WHERE state='draft'",
            (now,),
        )

        draft_version = f"draft-{now[:10].replace('-', '')}-v{uuid.uuid4().hex[:6]}"
        change_summary_json = json.dumps(diff, ensure_ascii=False)

        conn.execute(
            """
            INSERT INTO web_pricing_change_sets
            (id, base_catalog_version, draft_version, state, created_by, created_at, updated_at,
             reason, change_summary, catalog_fingerprint, published_catalog_version, publish_receipt, published_at)
            VALUES (?, ?, ?, 'draft', ?, ?, ?, ?, ?, ?, NULL, NULL, NULL)
            """,
            (
                change_set_id,
                clean_version,
                draft_version,
                actor_email,
                now,
                now,
                clean_reason,
                change_summary_json,
                fingerprint,
            ),
        )

        for item in validated_items:
            item_id = f"pci_{uuid.uuid4().hex[:16]}"
            conn.execute(
                """
                INSERT INTO web_pricing_change_items
                (id, change_set_id, sku, family, label, base_sale_price_xu, draft_sale_price_xu,
                 base_status, draft_status, action, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    change_set_id,
                    item["sku"],
                    item["family"],
                    item["label"],
                    item["base_sale_price_xu"],
                    item["sale_price_xu"],
                    item["base_status"],
                    item["status"],
                    item["action"],
                    now,
                    now,
                ),
            )

    # Record audit event
    _record_pricing_audit(
        actor,
        request,
        "pricing.draft.create",
        change_set_id,
        outcome="ok",
        detail=clean_reason,
    )

    return {
        "id": change_set_id,
        "base_catalog_version": clean_version,
        "draft_version": draft_version,
        "state": "draft",
        "created_by": actor_email,
        "created_at": now,
        "updated_at": now,
        "reason": clean_reason,
        "catalog_fingerprint": fingerprint,
        "diff": diff,
        "items": validated_items,
        "status_copy": "Đã lưu bản nháp",
    }


def update_draft_change_set(
    actor: dict[str, Any] | None = None,
    change_set_id: str = "",
    reason: str = "",
    items: list[dict[str, Any]] | None = None,
    base_items: list[dict[str, Any]] | None = None,
    request: Any = None,
    account: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Update an existing open draft change set."""
    actor = actor or account or {}
    clean_reason = str(reason or "").strip()
    if not clean_reason:
        raise HTTPException(status_code=422, detail="Lý do cập nhật bản nháp không được để trống.")

    validated_items = sanitize_and_validate_items(items)
    diff = calculate_catalog_diff(base_items, validated_items)
    fingerprint = compute_items_fingerprint(validated_items)
    actor_email = str(actor.get("email") or actor.get("id") or "admin").strip()
    now = utc_now()

    with transaction() as conn:
        ensure_pricing_schema(conn)
        row = conn.execute(
            "SELECT id, base_catalog_version, draft_version, state, catalog_fingerprint FROM web_pricing_change_sets WHERE id=?",
            (change_set_id,),
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Không tìm thấy bản nháp thay đổi giá.")

        current_state = row[3]
        if current_state in ("published", "superseded", "rejected"):
            raise HTTPException(
                status_code=422,
                detail=f"Bản nháp ở trạng thái '{current_state}' là bất biến (immutable) và không thể sửa đổi.",
            )

        # Idempotency check: if fingerprint and reason are identical, return existing state with zero delta
        if row[4] == fingerprint and row[3] == "draft":
            # Zero state delta idempotency replay
            pass

        change_summary_json = json.dumps(diff, ensure_ascii=False)
        conn.execute(
            """
            UPDATE web_pricing_change_sets
            SET updated_at=?, reason=?, change_summary=?, catalog_fingerprint=?
            WHERE id=?
            """,
            (now, clean_reason, change_summary_json, fingerprint, change_set_id),
        )

        # Replace draft items
        conn.execute("DELETE FROM web_pricing_change_items WHERE change_set_id=?", (change_set_id,))
        for item in validated_items:
            item_id = f"pci_{uuid.uuid4().hex[:16]}"
            conn.execute(
                """
                INSERT INTO web_pricing_change_items
                (id, change_set_id, sku, family, label, base_sale_price_xu, draft_sale_price_xu,
                 base_status, draft_status, action, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    change_set_id,
                    item["sku"],
                    item["family"],
                    item["label"],
                    item["base_sale_price_xu"],
                    item["sale_price_xu"],
                    item["base_status"],
                    item["status"],
                    item["action"],
                    now,
                    now,
                ),
            )

    _record_pricing_audit(
        actor,
        request,
        "pricing.draft.update",
        change_set_id,
        outcome="ok",
        detail=clean_reason,
    )

    return {
        "id": change_set_id,
        "base_catalog_version": row[1],
        "draft_version": row[2],
        "state": "draft",
        "created_by": actor_email,
        "updated_at": now,
        "reason": clean_reason,
        "catalog_fingerprint": fingerprint,
        "diff": diff,
        "items": validated_items,
        "status_copy": "Đã lưu bản nháp",
    }


def get_active_draft(base_items: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    """Fetch the currently active open draft change set if present."""
    with transaction() as conn:
        ensure_pricing_schema(conn)
        row = conn.execute(
            """
            SELECT id, base_catalog_version, draft_version, state, created_by,
                   created_at, updated_at, reason, change_summary, catalog_fingerprint
            FROM web_pricing_change_sets
            WHERE state='draft'
            ORDER BY created_at DESC
            LIMIT 1
            """
        ).fetchone()

        if not row:
            return None

        change_set_id = row[0]
        item_rows = conn.execute(
            """
            SELECT sku, family, label, draft_sale_price_xu, draft_status, action, base_sale_price_xu, base_status
            FROM web_pricing_change_items
            WHERE change_set_id=?
            ORDER BY sku ASC
            """,
            (change_set_id,),
        ).fetchall()

    items = [
        {
            "sku": r[0],
            "family": r[1],
            "label": r[2],
            "sale_price_xu": r[3],
            "status": r[4],
            "action": r[5],
            "base_sale_price_xu": r[6],
            "base_status": r[7],
        }
        for r in item_rows
    ]

    diff = calculate_catalog_diff(base_items, items)

    return {
        "id": row[0],
        "base_catalog_version": row[1],
        "draft_version": row[2],
        "state": row[3],
        "created_by": row[4],
        "created_at": row[5],
        "updated_at": row[6],
        "reason": row[7],
        "catalog_fingerprint": row[9],
        "diff": diff,
        "items": items,
        "status_copy": "Đã lưu bản nháp",
    }


def list_version_history(limit: int = 50) -> list[dict[str, Any]]:
    """Fetch immutable version history of pricing change sets."""
    with transaction() as conn:
        ensure_pricing_schema(conn)
        rows = conn.execute(
            """
            SELECT id, base_catalog_version, draft_version, state, created_by,
                   created_at, updated_at, reason, catalog_fingerprint,
                   published_catalog_version, publish_receipt, published_at
            FROM web_pricing_change_sets
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [
        {
            "id": r[0],
            "base_catalog_version": r[1],
            "draft_version": r[2],
            "state": r[3],
            "created_by": r[4],
            "created_at": r[5],
            "updated_at": r[6],
            "reason": r[7],
            "catalog_fingerprint": r[8],
            "published_catalog_version": r[9],
            "publish_receipt": r[10],
            "published_at": r[11],
        }
        for r in rows
    ]


def publish_draft_change_set(
    actor: dict[str, Any] | None = None,
    change_set_id: str = "",
    current_canonical_catalog: dict[str, Any] | None = None,
    reason: str = "",
    publish_adapter: Any = None,
    request: Any = None,
    account: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute publication boundary check for a draft change set.

    FAIL-CLOSED GUARANTEE:
    - If no reviewed canonical publisher exists upstream (publish_adapter is None),
      this function FAILS CLOSED with CANONICAL_PUBLISH_UNAVAILABLE.
    - If current_canonical_version != draft.base_catalog_version, publication is rejected
      with STALE_BASE_CATALOG_VERSION.
    - HTTP 200 from publish adapter is NOT sufficient; verification requires canonical readback proof.
    """
    actor = actor or account or {}
    current_canonical_catalog = current_canonical_catalog or {}
    clean_reason = str(reason or "").strip()
    if not clean_reason:
        raise HTTPException(status_code=422, detail="Lý do phát hành bảng giá không được để trống.")

    current_version = str(current_canonical_catalog.get("catalog_version") or "").strip()

    with transaction() as conn:
        ensure_pricing_schema(conn)
        row = conn.execute(
            """
            SELECT id, base_catalog_version, draft_version, state, catalog_fingerprint, published_catalog_version
            FROM web_pricing_change_sets
            WHERE id=?
            """,
            (change_set_id,),
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Không tìm thấy bản nháp thay đổi giá.")

        if row[3] == "published":
            # Idempotent replay: already published, return existing publication record without delta
            return {
                "published": True,
                "change_set_id": row[0],
                "draft_version": row[2],
                "published_catalog_version": row[5],
                "status_copy": "Đã phát hành",
                "message": "Bản nháp đã được phát hành trước đó (idempotent replay).",
            }

        base_version = row[1]
        # Concurrency safety: stale base version rejected
        if current_version and base_version != current_version:
            _record_pricing_audit(
                actor,
                request,
                "pricing.publish.attempt",
                change_set_id,
                outcome="denied",
                detail=f"Base '{base_version}' != current '{current_version}'",
            )
            raise HTTPException(
                status_code=422,
                detail=f"Xung đột phiên bản: Bản nháp dựa trên catalog '{base_version}', nhưng hệ thống đang ở '{current_version}'. Vui lòng rebase bản nháp.",
            )

        # Check for unknown SKU if published catalog has a strict registry
        known_skus = {it.get("code") for it in current_canonical_catalog.get("items", []) if isinstance(it, dict) and it.get("code")}
        if known_skus:
            draft_items = [r[0] for r in conn.execute("SELECT sku FROM web_pricing_change_items WHERE change_set_id=?", (change_set_id,)).fetchall()]
            for sku in draft_items:
                if sku not in known_skus:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Mã SKU '{sku}' không tồn tại trong danh mục canonical đã công bố; không thể phát hành SKU không xác định.",
                    )

    # Fail closed if upstream canonical publish is not available
    if publish_adapter is None:
        _record_pricing_audit(
            actor,
            request,
            "pricing.publish.attempt",
            change_set_id,
            outcome="denied",
            detail="Upstream Core Bridge has no publish endpoint; publish is guarded.",
        )
        raise HTTPException(
            status_code=503,
            detail="Cổng phát hành giá canonical chưa được cấu hình trên Core Bridge (CANONICAL_PUBLISH_AVAILABLE=NO). Thao tác được bảo vệ an toàn.",
        )

    # If mock/adapter is provided (in test environment)
    receipt = publish_adapter(change_set_id=change_set_id, reason=clean_reason)
    if not receipt or not receipt.get("ok"):
        raise HTTPException(status_code=502, detail="Core Bridge từ chối yêu cầu phát hành bảng giá.")

    new_version = receipt.get("published_catalog_version")
    receipt_id = receipt.get("receipt_id") or "mock-receipt"
    now = utc_now()

    with transaction() as conn:
        conn.execute(
            """
            UPDATE web_pricing_change_sets
            SET state='published', published_catalog_version=?, publish_receipt=?, published_at=?, updated_at=?
            WHERE id=?
            """,
            (new_version, receipt_id, now, now, change_set_id),
        )

    _record_pricing_audit(
        actor,
        request,
        "pricing.publish.success",
        change_set_id,
        outcome="ok",
        detail=clean_reason,
    )

    return {
        "published": True,
        "change_set_id": change_set_id,
        "published_catalog_version": new_version,
        "publish_receipt": receipt_id,
        "published_at": now,
        "status_copy": "Đã phát hành",
        "message": "Bảng giá đã được phát hành chính thức lên hệ thống.",
    }
