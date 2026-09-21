"""Server-side WebApp Admin Commercial Products Module.

Provides authenticated Admin endpoints proxying canonical product catalog and
CAS mutation requests to Bot Core via Core Bridge.

Endpoints:
- GET   /api/admin/commercial/products
- GET   /api/admin/commercial/products/{product_key}
- PATCH /api/admin/commercial/products/{product_key}

Also mounted at /api/v1/admin/commercial/products for API version parity.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from copyfast_auth import (
    _request_id,
    require_admin,
    require_admin_csrf,
    require_canonical_admin,
    require_canonical_admin_csrf,
)
import copyfast_bridge


LOGGER = logging.getLogger("copyfast_admin_commercial")

router = APIRouter(tags=["Admin Commercial"])

# Strict editable field whitelist as governed by Bot Commercial Authority contract
EDITABLE_PRODUCT_FIELDS = frozenset({
    "display_name",
    "description",
    "product_group",
    "public_visible",
    "commercial_enabled",
    "sort_order",
})

# Technical fields that MUST NEVER be mutated through commercial administration
IMMUTABLE_TECHNICAL_FIELDS = frozenset({
    "execution_enabled",
    "execution_blocker",
    "supported_tiers",
    "supported_quality_tiers",
    "supported_ratios",
    "provider_capability",
    "required_capability",
    "modality",
    "executor_product_type",
    "engine_route",
    "pricing",
    "xu",
    "provider_config",
    "wallet",
    "routing_secrets",
})


class ProductPatchRequest(BaseModel):
    expected_version: int = Field(..., ge=0, description="Canonical CAS version expected by caller")
    changes: dict[str, Any] = Field(..., description="Map of editable field changes")
    reason: str = Field(..., min_length=1, max_length=500, description="Mandatory audit explanation for mutation")


def _clean_product_key(raw_key: str) -> str:
    cleaned = str(raw_key or "").strip().lower()
    if not cleaned or len(cleaned) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã sản phẩm không hợp lệ",
        )
    return cleaned


def _validate_patch_changes(changes: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(changes, dict) or not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Danh sách thay đổi (changes) không được để trống",
        )

    sanitized_changes: dict[str, Any] = {}
    for key, value in changes.items():
        clean_key = str(key or "").strip().lower()
        if clean_key in IMMUTABLE_TECHNICAL_FIELDS or clean_key not in EDITABLE_PRODUCT_FIELDS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Trường '{clean_key}' là trường kỹ thuật bất biến hoặc không thuộc danh mục cho phép chỉnh sửa",
            )
        if clean_key in {"display_name", "description", "product_group"}:
            sanitized_changes[clean_key] = str(value or "").strip()
        elif clean_key in {"public_visible", "commercial_enabled"}:
            sanitized_changes[clean_key] = bool(value)
        elif clean_key == "sort_order":
            try:
                sanitized_changes[clean_key] = int(value)
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Giá trị sort_order phải là số nguyên",
                )

    if not sanitized_changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không có trường hợp lệ nào để cập nhật",
        )
    return sanitized_changes


# ─── GET COLLECTION ───────────────────────────────────────────────────────────

@router.get("/api/admin/commercial/products")
@router.get("/api/v1/admin/commercial/products")
async def get_admin_commercial_products(
    request: Request,
    account: dict = Depends(require_canonical_admin),
):
    """Retrieve canonical Bot product collection for Admin Commercial center."""
    actor_id = str(account.get("canonical_user_id") or account.get("id") or "")
    req_id = _request_id(request)

    bridge_res = await copyfast_bridge.bridge_request(
        "GET",
        "/internal/v1/admin/products",
        request_id=req_id,
        actor_id=actor_id,
    )

    if not bridge_res.get("ok"):
        return bridge_res

    data = bridge_res.get("data") or {}
    products = data.get("products") or []

    return {
        "ok": True,
        "status": "completed",
        "message": "Nạp danh mục sản phẩm canonical thành công",
        "data": {
            "count": len(products),
            "products": products,
            "read_only_technical_fields": list(IMMUTABLE_TECHNICAL_FIELDS),
            "editable_fields": list(EDITABLE_PRODUCT_FIELDS),
        },
    }


# ─── GET SINGLE PRODUCT ───────────────────────────────────────────────────────

@router.get("/api/admin/commercial/products/{product_key}")
@router.get("/api/v1/admin/commercial/products/{product_key}")
async def get_admin_commercial_product_single(
    product_key: str,
    request: Request,
    account: dict = Depends(require_canonical_admin),
):
    """Retrieve single canonical product configuration from Bot Core."""
    clean_key = _clean_product_key(product_key)
    actor_id = str(account.get("canonical_user_id") or account.get("id") or "")
    req_id = _request_id(request)

    bridge_res = await copyfast_bridge.bridge_request(
        "GET",
        f"/internal/v1/admin/products/{clean_key}",
        request_id=req_id,
        actor_id=actor_id,
    )

    if not bridge_res.get("ok"):
        return bridge_res

    return bridge_res


# ─── PATCH PRODUCT ────────────────────────────────────────────────────────────

@router.patch("/api/admin/commercial/products/{product_key}")
@router.patch("/api/v1/admin/commercial/products/{product_key}")
async def patch_admin_commercial_product(
    product_key: str,
    payload: ProductPatchRequest,
    request: Request,
    response: Response,
    account: dict = Depends(require_canonical_admin_csrf),
):
    """Execute CAS optimistic mutation on canonical product commercial presentation."""
    clean_key = _clean_product_key(product_key)
    clean_reason = str(payload.reason or "").strip()
    if not clean_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lý do chỉnh sửa (reason) là bắt buộc",
        )

    validated_changes = _validate_patch_changes(payload.changes)
    actor_id = str(account.get("canonical_user_id") or account.get("id") or "")
    req_id = _request_id(request)

    bot_payload = {
        "expected_version": payload.expected_version,
        "changes": validated_changes,
        "reason": clean_reason,
    }

    # Execute atomic CAS PATCH against Bot Core
    # CoreBridgeClient guarantees NO_BLIND_REPLAY (attempts=1) for PATCH mutations
    bridge_res = await copyfast_bridge.bridge_request(
        "PATCH",
        f"/internal/v1/admin/products/{clean_key}",
        payload=bot_payload,
        request_id=req_id,
        actor_id=actor_id,
    )

    if not bridge_res.get("ok"):
        err_code = bridge_res.get("error_code")
        if err_code == "VERSION_CONFLICT_STALE_WRITE" or "conflict" in str(bridge_res).lower():
            response.status_code = status.HTTP_409_CONFLICT
            return {
                "ok": False,
                "status": "conflict",
                "error_code": "VERSION_CONFLICT_STALE_WRITE",
                "message": bridge_res.get("message") or "Dữ liệu đã bị thay đổi ở phiên khác. Vui lòng tải lại để đồng bộ.",
                "data": bridge_res.get("data") or {},
            }
        return bridge_res

    patch_data = bridge_res.get("data") or {}
    new_version = patch_data.get("new_version")
    prev_version = patch_data.get("previous_version")
    write_receipt = patch_data.get("write_receipt")
    effective_product = patch_data.get("effective_product")

    # Invariant checks for write success
    if (
        new_version is None
        or prev_version is None
        or new_version <= prev_version
        or not write_receipt
        or not effective_product
    ):
        return {
            "ok": False,
            "status": "guarded",
            "error_code": "CANONICAL_INVALID_RESPONSE",
            "message": "Phản hồi từ Bot Core không thỏa mãn hợp đồng xác nhận ghi canonical.",
            "data": {},
        }

    # Mandatory Post-Patch GET Readback (POST_PATCH_GET_READBACK=YES)
    readback_res = await copyfast_bridge.bridge_request(
        "GET",
        f"/internal/v1/admin/products/{clean_key}",
        request_id=_request_id(request),
        actor_id=actor_id,
    )

    readback_data = readback_res.get("data") or {}
    readback_effective = readback_data.get("effective") or {}
    readback_version = readback_effective.get("version", readback_data.get("version"))

    # Verify committed changes and version against readback
    readback_match = True
    if readback_version != new_version:
        readback_match = False

    for k, v in validated_changes.items():
        if readback_effective.get(k) != v:
            readback_match = False
            break

    if not readback_match:
        LOGGER.error(
            "Readback verification failed for product %s: expected version=%s got=%s",
            clean_key,
            new_version,
            readback_version,
        )
        return {
            "ok": False,
            "status": "failed",
            "error_code": "READBACK_VERIFICATION_FAILED",
            "message": "Ghi nhận thành công nhưng kiểm tra đối soát (readback) không trùng khớp dữ liệu.",
            "data": {
                "product_key": clean_key,
                "readback_verified": False,
            },
        }

    return {
        "ok": True,
        "status": "completed",
        "message": f"Cập nhật sản phẩm '{clean_key}' thành công và đã xác minh canonical readback.",
        "data": {
            "product_key": clean_key,
            "previous_version": prev_version,
            "new_version": new_version,
            "accepted_changes": validated_changes,
            "write_receipt": write_receipt,
            "effective_product": readback_effective,
            "readback_verified": True,
            "verification_status": "CANONICAL_WRITE_VERIFIED",
        },
    }
