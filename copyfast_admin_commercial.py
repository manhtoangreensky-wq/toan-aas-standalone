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


# ─── CANONICAL PACKAGES AUTHORITY CONTRACT (SPEC-B03) ──────────────────────────

IMMUTABLE_PACKAGE_FIELDS: frozenset[str] = frozenset({
    "package_key",
    "package_type",
    "duration_days",
    "benefits",
    "items",
    "plan_xu",
    "required_member_tier",
    "group",
    "read_authority",
    "quote_authority",
    "entitlement_authority",
    "wallet_mutations",
    "ledger",
    "historical_purchases",
    "balance",
    "credits",
    "cost",
    "cost_minor",
    "cost_vnd",
    "provider",
    "provider_cost",
    "provider_key",
    "provider_costs",
})

EDITABLE_PACKAGE_FIELDS: frozenset[str] = frozenset({
    "display_name",
    "description",
    "price_vnd",
    "public_visible",
    "commercial_enabled",
    "sort_order",
})


class PackagePatchRequest(BaseModel):
    expected_version: int = Field(..., ge=0, description="Canonical CAS version expected by caller")
    changes: dict[str, Any] = Field(..., description="Dictionary of fields to mutate")
    reason: str = Field(..., min_length=1, max_length=500, description="Mandatory audit explanation for mutation")


def _clean_package_key(raw_key: str) -> str:
    cleaned = str(raw_key or "").strip().lower()
    if not cleaned or len(cleaned) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã gói dịch vụ không hợp lệ",
        )
    return cleaned


def _sanitize_and_validate_package_changes(changes: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(changes, dict) or not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Danh sách thay đổi không được để trống",
        )

    sanitized: dict[str, Any] = {}
    for key, val in changes.items():
        clean_k = str(key or "").strip()
        if clean_k in IMMUTABLE_PACKAGE_FIELDS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Trường '{clean_k}' là bất biến và không thể chỉnh sửa",
            )
        if clean_k not in EDITABLE_PACKAGE_FIELDS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Trường '{clean_k}' không được phép chỉnh sửa",
            )

        if clean_k == "display_name":
            str_val = str(val or "").strip()
            if not str_val or len(str_val) > 160:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tên hiển thị gói cước phải từ 1 đến 160 ký tự",
                )
            sanitized["display_name"] = str_val
        elif clean_k == "description":
            str_val = str(val or "").strip()
            if len(str_val) > 500:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Mô tả gói cước không được vượt quá 500 ký tự",
                )
            sanitized["description"] = str_val
        elif clean_k == "price_vnd":
            try:
                int_val = int(val)
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Giá niêm yết price_vnd phải là số nguyên",
                )
            if int_val < 0 or int_val > 100_000_000:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Giá niêm yết price_vnd phải trong khoảng từ 0 đến 100,000,000 VND",
                )
            sanitized["price_vnd"] = int_val
        elif clean_k == "public_visible":
            if not isinstance(val, bool):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Trường public_visible phải là boolean (true/false)",
                )
            sanitized["public_visible"] = bool(val)
        elif clean_k == "commercial_enabled":
            if not isinstance(val, bool):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Trường commercial_enabled phải là boolean (true/false)",
                )
            sanitized["commercial_enabled"] = bool(val)
        elif clean_k == "sort_order":
            try:
                int_val = int(val)
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Thứ tự sort_order phải là số nguyên",
                )
            if int_val < 0 or int_val > 100_000:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Thứ tự sort_order phải trong khoảng từ 0 đến 100,000",
                )
            sanitized["sort_order"] = int_val

    if not sanitized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không có trường hợp lệ nào để cập nhật",
        )
    return sanitized


# ─── GET PACKAGES COLLECTION ─────────────────────────────────────────────────

@router.get("/api/admin/commercial/packages")
@router.get("/api/v1/admin/commercial/packages")
async def get_admin_commercial_packages_collection(
    request: Request,
    account: dict = Depends(require_canonical_admin),
):
    """Retrieve canonical packages collection from Bot Core (SPEC-B03)."""
    actor_id = str(account.get("canonical_user_id") or account.get("id") or "")
    req_id = _request_id(request)

    bridge_res = await copyfast_bridge.bridge_request(
        "GET",
        "/internal/v1/admin/packages",
        request_id=req_id,
        actor_id=actor_id,
    )

    if not bridge_res.get("ok"):
        return bridge_res

    packages_list = bridge_res.get("packages") or (bridge_res.get("data") or {}).get("packages") or []
    catalog_version = bridge_res.get("catalog_version")
    if catalog_version is None and isinstance(bridge_res.get("data"), dict):
        catalog_version = bridge_res["data"].get("catalog_version")

    proven_domains = bridge_res.get("proven_domains")
    if proven_domains is None and isinstance(bridge_res.get("data"), dict):
        proven_domains = bridge_res["data"].get("proven_domains")

    return {
        "ok": True,
        "status": "completed",
        "message": "Nạp danh mục gói cước canonical thành công",
        "data": {
            "count": len(packages_list),
            "packages": packages_list,
            "catalog_version": catalog_version,
            "proven_domains": proven_domains,
        },
    }


# ─── GET SINGLE PACKAGE ───────────────────────────────────────────────────────

@router.get("/api/admin/commercial/packages/{package_key}")
@router.get("/api/v1/admin/commercial/packages/{package_key}")
async def get_admin_commercial_package_single(
    package_key: str,
    request: Request,
    account: dict = Depends(require_canonical_admin),
):
    """Retrieve single canonical package from Bot Core (SPEC-B03)."""
    clean_key = _clean_package_key(package_key)
    actor_id = str(account.get("canonical_user_id") or account.get("id") or "")
    req_id = _request_id(request)

    bridge_res = await copyfast_bridge.bridge_request(
        "GET",
        f"/internal/v1/admin/packages/{clean_key}",
        request_id=req_id,
        actor_id=actor_id,
    )

    if not bridge_res.get("ok"):
        return bridge_res

    single_pkg = bridge_res.get("package") or (bridge_res.get("data") or {}).get("package") or {}
    return {
        "ok": True,
        "status": "completed",
        "message": "Nạp chi tiết gói cước thành công",
        "data": {
            "package_key": clean_key,
            "package": single_pkg,
        },
    }


# ─── PATCH PACKAGE ────────────────────────────────────────────────────────────

@router.patch("/api/admin/commercial/packages/{package_key}")
@router.patch("/api/v1/admin/commercial/packages/{package_key}")
async def patch_admin_commercial_package(
    package_key: str,
    payload: PackagePatchRequest,
    request: Request,
    response: Response,
    account: dict = Depends(require_canonical_admin_csrf),
):
    """Update single canonical package via Bot Core CAS mutation with audit (SPEC-B03)."""
    clean_key = _clean_package_key(package_key)
    clean_reason = str(payload.reason or "").strip()
    if not clean_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lý do điều chỉnh (reason) là bắt buộc cho audit trail",
        )

    sanitized_changes = _sanitize_and_validate_package_changes(payload.changes)

    actor_id = str(account.get("canonical_user_id") or account.get("id") or "")
    req_id = _request_id(request)

    # Server-Side Defense: read canonical editability from fresh Bot package GET
    cur_res = await copyfast_bridge.bridge_request(
        "GET",
        f"/internal/v1/admin/packages/{clean_key}",
        request_id=req_id,
        actor_id=actor_id,
    )
    if not cur_res or not cur_res.get("ok"):
        response.status_code = status.HTTP_502_BAD_GATEWAY
        return {
            "ok": False,
            "status": "failed",
            "error_code": "BOT_PACKAGE_UNAVAILABLE",
            "message": "Không thể kiểm tra năng lực chỉnh sửa từ Bot Core.",
            "data": {},
        }

    cur_pkg = cur_res.get("package") or (cur_res.get("data") or {}).get("package") or {}
    field_classifications = cur_pkg.get("field_classifications") or {}
    editable_commercial = field_classifications.get("editable_commercial")
    field_effect_scopes = field_classifications.get("field_effect_scopes") or {}

    for field_name in sanitized_changes.keys():
        if field_effect_scopes.get(field_name) == "IMMUTABLE":
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {
                "ok": False,
                "status": "guarded",
                "error_code": "IMMUTABLE_FIELD_REJECTED",
                "message": f"Trường '{field_name}' là bất biến (IMMUTABLE) theo quy chuẩn Bot Core.",
                "data": {"field": field_name},
            }
        if isinstance(editable_commercial, list) and field_name not in editable_commercial:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {
                "ok": False,
                "status": "guarded",
                "error_code": "FIELD_NOT_EDITABLE_FOR_PACKAGE",
                "message": f"Trường '{field_name}' không thuộc danh mục cho phép chỉnh sửa của gói.",
                "data": {"field": field_name},
            }

    bot_payload = {
        "expected_version": payload.expected_version,
        "changes": sanitized_changes,
        "reason": clean_reason,
    }

    # Execute atomic CAS PATCH against Bot Core
    bridge_res = await copyfast_bridge.bridge_request(
        "PATCH",
        f"/internal/v1/admin/packages/{clean_key}",
        payload=bot_payload,
        request_id=req_id,
        actor_id=actor_id,
    )

    if not bridge_res.get("ok"):
        err_code = bridge_res.get("error_code")
        if err_code == "VERSION_CONFLICT" or "conflict" in str(bridge_res).lower():
            response.status_code = status.HTTP_409_CONFLICT
            return {
                "ok": False,
                "status": "conflict",
                "error_code": "VERSION_CONFLICT",
                "message": bridge_res.get("message") or "Dữ liệu đã bị thay đổi ở phiên khác. Vui lòng tải lại để đồng bộ.",
                "data": bridge_res.get("data") or {},
            }
        if err_code in {
            "IMMUTABLE_FIELD_REJECTED",
            "FIELD_NOT_EDITABLE_FOR_TYPE",
            "UNKNOWN_FIELD_REJECTED",
            "EXPECTED_VERSION_MANDATORY",
            "CHANGES_MANDATORY",
            "REASON_MANDATORY",
            "INVALID_DISPLAY_NAME",
            "INVALID_DESCRIPTION",
            "INVALID_PRICE_VND",
            "PRICE_VND_OUT_OF_BOUNDS",
            "INVALID_PUBLIC_VISIBLE",
            "INVALID_COMMERCIAL_ENABLED",
            "INVALID_SORT_ORDER",
            "SORT_ORDER_OUT_OF_BOUNDS",
        }:
            response.status_code = status.HTTP_400_BAD_REQUEST
        else:
            response.status_code = status.HTTP_502_BAD_GATEWAY
        return bridge_res

    # Canonical receipt validation
    res_data = bridge_res.get("data") if isinstance(bridge_res.get("data"), dict) else {}
    receipt_data = bridge_res.get("receipt") or res_data.get("receipt")
    receipt_id = (
        bridge_res.get("receipt_id")
        or res_data.get("receipt_id")
        or (receipt_data.get("receipt_id") if isinstance(receipt_data, dict) else None)
    )
    new_version = (
        bridge_res.get("new_version")
        or res_data.get("new_version")
        or (receipt_data.get("new_version") if isinstance(receipt_data, dict) else None)
    )
    prev_version = (
        bridge_res.get("previous_version")
        or res_data.get("previous_version")
        or (receipt_data.get("previous_version") if isinstance(receipt_data, dict) else None)
    )

    if not receipt_id:
        LOGGER.error("Bot Core response missing receipt_id: %s", bridge_res)
        response.status_code = status.HTTP_502_BAD_GATEWAY
        return {
            "ok": False,
            "status": "failed",
            "error_code": "MISSING_RECEIPT_ID",
            "message": "Phản hồi từ Bot Core thiếu receipt_id xác nhận.",
            "data": {},
        }

    if new_version is None:
        LOGGER.error("Bot Core response missing new_version: %s", bridge_res)
        response.status_code = status.HTTP_502_BAD_GATEWAY
        return {
            "ok": False,
            "status": "failed",
            "error_code": "MISSING_NEW_VERSION",
            "message": "Phản hồi từ Bot Core thiếu new_version hợp lệ.",
            "data": {},
        }

    if prev_version is None or not (isinstance(new_version, int) and isinstance(prev_version, int) and new_version > prev_version):
        LOGGER.error("Bot Core invalid version advance: prev=%s, new=%s", prev_version, new_version)
        response.status_code = status.HTTP_502_BAD_GATEWAY
        return {
            "ok": False,
            "status": "failed",
            "error_code": "INVALID_VERSION_ADVANCE",
            "message": f"Bước nhảy phiên bản không hợp lệ: previous={prev_version}, new={new_version}.",
            "data": {},
        }

    patch_receipt = (
        receipt_data
        if (isinstance(receipt_data, dict) and receipt_data.get("receipt_id"))
        else {
            "receipt_id": receipt_id,
            "previous_version": prev_version,
            "new_version": new_version,
            "accepted_changes": bridge_res.get("accepted_changes") or res_data.get("accepted_changes") or sanitized_changes,
            "mutation_digest": bridge_res.get("mutation_digest") or res_data.get("mutation_digest"),
            "request_id": bridge_res.get("request_id") or res_data.get("request_id"),
        }
    )

    # Mandatory Post-Patch GET Readback (POST_PATCH_GET_READBACK=YES)
    readback_res = await copyfast_bridge.bridge_request(
        "GET",
        f"/internal/v1/admin/packages/{clean_key}",
        request_id=req_id,
        actor_id=actor_id,
    )

    if not readback_res or not readback_res.get("ok"):
        LOGGER.error("Readback fresh GET failed or unavailable for package %s: %s", clean_key, readback_res)
        response.status_code = status.HTTP_502_BAD_GATEWAY
        return {
            "ok": False,
            "status": "failed",
            "error_code": "READBACK_UNAVAILABLE",
            "message": "Ghi nhận mutation thành công nhưng fresh GET readback đối soát không khả dụng.",
            "data": {
                "package_key": clean_key,
                "readback_verified": False,
                "verification_status": "READBACK_UNAVAILABLE",
            },
        }

    readback_pkg = readback_res.get("package") or (readback_res.get("data") or {}).get("package") or {}
    if not readback_pkg:
        LOGGER.error("Readback fresh GET returned empty package for %s: %s", clean_key, readback_res)
        response.status_code = status.HTTP_502_BAD_GATEWAY
        return {
            "ok": False,
            "status": "failed",
            "error_code": "READBACK_PACKAGE_MISSING",
            "message": "Đối soát thất bại: không tìm thấy gói cước sau khi cập nhật.",
            "data": {
                "package_key": clean_key,
                "readback_verified": False,
                "verification_status": "READBACK_PACKAGE_MISSING",
            },
        }

    readback_version = readback_pkg.get("version")
    if readback_version != new_version:
        LOGGER.error(
            "Readback version mismatch for package %s: expected version=%s got=%s",
            clean_key,
            new_version,
            readback_version,
        )
        response.status_code = status.HTTP_502_BAD_GATEWAY
        return {
            "ok": False,
            "status": "failed",
            "error_code": "READBACK_VERSION_MISMATCH",
            "message": f"Đối soát thất bại: phiên bản đọc lại (v{readback_version}) không khớp phiên bản mới (v{new_version}).",
            "data": {
                "package_key": clean_key,
                "expected_version": new_version,
                "readback_version": readback_version,
                "readback_verified": False,
                "verification_status": "READBACK_VERSION_MISMATCH",
            },
        }

    for k, expected_v in sanitized_changes.items():
        if readback_pkg.get(k) != expected_v:
            LOGGER.error(
                "Readback field mismatch for package %s field %s: expected=%s got=%s",
                clean_key,
                k,
                expected_v,
                readback_pkg.get(k),
            )
            response.status_code = status.HTTP_502_BAD_GATEWAY
            return {
                "ok": False,
                "status": "failed",
                "error_code": "READBACK_FIELD_MISMATCH",
                "message": f"Đối soát thất bại: trường '{k}' sau khi đọc lại ({readback_pkg.get(k)}) không khớp giá trị vừa ghi ({expected_v}).",
                "data": {
                    "package_key": clean_key,
                    "field": k,
                    "expected": expected_v,
                    "got": readback_pkg.get(k),
                    "readback_verified": False,
                    "verification_status": "READBACK_FIELD_MISMATCH",
                },
            }

    return {
        "ok": True,
        "status": "completed",
        "message": f"Cập nhật gói dịch vụ '{clean_key}' thành công và đã xác minh canonical readback.",
        "data": {
            "package_key": clean_key,
            "previous_version": prev_version,
            "new_version": new_version,
            "accepted_changes": sanitized_changes,
            "write_receipt": patch_receipt,
            "effective_package": readback_pkg,
            "readback_verified": True,
            "verification_status": "BOT_CORE_READBACK_VERIFIED",
        },
    }
