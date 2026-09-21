"""Server-side WebApp Admin Commercial Products and Pricing Module.

Provides authenticated Admin endpoints proxying canonical product catalog,
pricing models, and CAS mutation requests to Bot Core via Core Bridge.

Endpoints:
- GET   /api/admin/commercial/products
- GET   /api/admin/commercial/products/{product_key}
- PATCH /api/admin/commercial/products/{product_key}
- GET   /api/admin/commercial/pricing
- GET   /api/admin/commercial/pricing/{price_key}
- PATCH /api/admin/commercial/pricing/{price_key}

Also mounted at /api/v1/admin/commercial/... for API version parity.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
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


# ─── CANONICAL PRICING AUTHORITY CONTRACT (SPEC-B02) ───────────────────────────

IMMUTABLE_INTERNAL_COST_FIELDS: frozenset[str] = frozenset({
    "cost",
    "cost_minor",
    "cost_vnd",
    "usd_per_scene",
    "usd_per_second",
    "usd_per_image",
    "usd_per_track",
    "provider",
    "provider_cost",
    "provider_key",
    "provider_costs",
    "provider_order",
    "provider_priority",
    "provider_sources",
    "provider_capability",
    "exchange_rates_vnd_per_usd",
    "usd_to_vnd",
    "vnd_per_usd",
    "margin",
    "profit",
    "credentials",
    "api_key",
    "token",
    "wallet",
    "balance",
    "ledger",
})


class PricePatchRequest(BaseModel):
    expected_version: int = Field(..., ge=0, description="Canonical CAS version expected by caller")
    new_value: Any = Field(..., description="New price value (numeric int or float)")
    reason: str = Field(..., min_length=1, max_length=500, description="Mandatory audit explanation for mutation")


def _clean_price_key(raw_key: str) -> str:
    cleaned = str(raw_key or "").strip().lower()
    if not cleaned or len(cleaned) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã định giá không hợp lệ",
        )
    return cleaned


# ─── GET PRICING COLLECTION ───────────────────────────────────────────────────

@router.get("/api/admin/commercial/pricing")
@router.get("/api/v1/admin/commercial/pricing")
async def get_admin_commercial_pricing_collection(
    request: Request,
    account: dict = Depends(require_canonical_admin),
):
    """Retrieve canonical pricing collection from Bot Core."""
    actor_id = str(account.get("canonical_user_id") or account.get("id") or "")
    req_id = _request_id(request)

    bridge_res = await copyfast_bridge.bridge_request(
        "GET",
        "/internal/v1/admin/pricing",
        request_id=req_id,
        actor_id=actor_id,
    )

    if not bridge_res.get("ok"):
        return bridge_res

    pricing_list = bridge_res.get("pricing") or (bridge_res.get("data") or {}).get("pricing") or []
    catalog_version = bridge_res.get("catalog_version")
    if catalog_version is None and isinstance(bridge_res.get("data"), dict):
        catalog_version = bridge_res["data"].get("catalog_version")

    return {
        "ok": True,
        "status": "completed",
        "message": "Nạp danh mục bảng giá thành công",
        "data": {
            "count": len(pricing_list),
            "pricing": pricing_list,
            "catalog_version": catalog_version,
        },
    }


# ─── GET SINGLE PRICING ───────────────────────────────────────────────────────

@router.get("/api/admin/commercial/pricing/{price_key}")
@router.get("/api/v1/admin/commercial/pricing/{price_key}")
async def get_admin_commercial_pricing_single(
    price_key: str,
    request: Request,
    account: dict = Depends(require_canonical_admin),
):
    """Retrieve single canonical pricing configuration from Bot Core."""
    clean_key = _clean_price_key(price_key)
    actor_id = str(account.get("canonical_user_id") or account.get("id") or "")
    req_id = _request_id(request)

    bridge_res = await copyfast_bridge.bridge_request(
        "GET",
        f"/internal/v1/admin/pricing/{clean_key}",
        request_id=req_id,
        actor_id=actor_id,
    )

    if not bridge_res.get("ok"):
        return bridge_res

    single_pricing = bridge_res.get("pricing") or (bridge_res.get("data") or {}).get("pricing") or {}
    return {
        "ok": True,
        "status": "completed",
        "message": "Nạp chi tiết định giá thành công",
        "data": {
            "price_key": clean_key,
            "pricing": single_pricing,
        },
    }


# ─── PATCH PRICING ────────────────────────────────────────────────────────────

@router.patch("/api/admin/commercial/pricing/{price_key}")
@router.patch("/api/v1/admin/commercial/pricing/{price_key}")
async def patch_admin_commercial_pricing(
    price_key: str,
    payload: PricePatchRequest,
    request: Request,
    response: Response,
    account: dict = Depends(require_canonical_admin_csrf),
):
    """Execute CAS optimistic mutation on canonical SKU pricing."""
    clean_key = _clean_price_key(price_key)
    clean_reason = str(payload.reason or "").strip()
    if not clean_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lý do chỉnh sửa (reason) là bắt buộc",
        )

    # Check for forbidden cost fields in raw json
    try:
        raw_json = await request.json()
        if isinstance(raw_json, dict):
            forbidden = set(raw_json.keys()) & IMMUTABLE_INTERNAL_COST_FIELDS
            if forbidden:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Payload contains forbidden internal cost fields: {sorted(forbidden)}",
                )
    except HTTPException:
        raise
    except Exception:
        pass

    raw_val = payload.new_value
    try:
        dec_val = Decimal(str(raw_val).strip())
    except (InvalidOperation, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Giá trị mới (new_value) phải là số hợp lệ",
        )

    if dec_val < Decimal("0"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Giá trị định giá không được là số âm",
        )

    if dec_val > Decimal("100000000"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Giá trị định giá vượt quá giới hạn tối đa cho phép (100,000,000)",
        )

    clean_val = int(dec_val) if dec_val == dec_val.to_integral_value() and "." not in str(raw_val) else float(dec_val)
    actor_id = str(account.get("canonical_user_id") or account.get("id") or "")
    req_id = _request_id(request)

    bot_payload = {
        "expected_version": payload.expected_version,
        "new_value": clean_val,
        "reason": clean_reason,
    }

    # Execute atomic CAS PATCH against Bot Core
    bridge_res = await copyfast_bridge.bridge_request(
        "PATCH",
        f"/internal/v1/admin/pricing/{clean_key}",
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
        if err_code in {
            "IMMUTABLE_PRICE_KEY_REJECTED",
            "NEGATIVE_PRICE_REJECTED",
            "PAID_PRICE_CANNOT_BE_ZERO",
            "INVALID_PRICE_VALUE",
            "INVALID_PRICE_VALUE_TYPE",
            "IMMUTABLE_FIELD_MODIFICATION_FORBIDDEN",
            "PRICE_VALUE_UNBOUNDED",
        }:
            response.status_code = status.HTTP_400_BAD_REQUEST
        return bridge_res

    patch_receipt = bridge_res.get("receipt") or (bridge_res.get("data") or {}).get("receipt") or {}
    patch_pricing = bridge_res.get("pricing") or (bridge_res.get("data") or {}).get("pricing") or {}

    new_version = patch_receipt.get("new_version") or patch_pricing.get("version")
    prev_version = patch_receipt.get("previous_version")

    # Invariant checks for write success
    if (
        new_version is None
        or prev_version is None
        or new_version <= prev_version
        or not patch_receipt
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
        f"/internal/v1/admin/pricing/{clean_key}",
        request_id=_request_id(request),
        actor_id=actor_id,
    )

    readback_pricing = readback_res.get("pricing") or (readback_res.get("data") or {}).get("pricing") or {}
    readback_version = readback_pricing.get("version")
    readback_effective_val = readback_pricing.get("effective_value")

    readback_match = True
    if readback_version != new_version:
        readback_match = False

    try:
        if Decimal(str(readback_effective_val)) != dec_val:
            readback_match = False
    except Exception:
        if readback_effective_val != clean_val:
            readback_match = False

    if not readback_match:
        LOGGER.error(
            "Readback verification failed for pricing %s: expected version=%s got=%s, expected val=%s got=%s",
            clean_key,
            new_version,
            readback_version,
            clean_val,
            readback_effective_val,
        )
        return {
            "ok": False,
            "status": "failed",
            "error_code": "READBACK_VERIFICATION_FAILED",
            "message": "Ghi nhận thành công nhưng kiểm tra đối soát (readback) không trùng khớp dữ liệu.",
            "data": {
                "price_key": clean_key,
                "readback_verified": False,
                "customer_effective_live_verified": False,
                "verification_status": "READBACK_VERIFICATION_FAILED",
            },
        }

    return {
        "ok": True,
        "status": "completed",
        "message": f"Cập nhật bảng giá '{clean_key}' thành công và đã xác minh canonical readback.",
        "data": {
            "price_key": clean_key,
            "previous_version": prev_version,
            "new_version": new_version,
            "new_value": clean_val,
            "write_receipt": patch_receipt,
            "effective_pricing": readback_pricing,
            "readback_verified": True,
            "customer_effective_live_verified": False,
            "verification_status": "BOT_CORE_READBACK_VERIFIED",
        },
    }

