"""Document Translate Canonical Job Bridge Adapter.

Task: WEBAPP_R6_REMAINING_13_ENGINE_GAPS_FULL_CLOSURE_MASTER_BATCH_R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1

Connects the Web customer flow (/documents/translate) for `documents_translate`
to a canonical translation job bridge contract without executing paid provider calls,
fake translations, or mock responses.

Invariants:
- Fail-Closed Admission: zero provider calls until Owner-authorized runtime execution.
- Truthful Status: initial status is 'queued', status_reason is
  'AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION'. Zero fake output, zero fake translation.
- Asset Vault Ownership: input document must be owned by authenticated Web account.
- Idempotency & Conflict: replay existing job on identical payload hash, reject with 409
  on same request_id / idempotency_key with differing payload.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import re
from typing import Any
import uuid

from fastapi import HTTPException
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction, utc_now

CANONICAL_PRODUCT_KEY = "documents_translate"
CANONICAL_ROUTING_KEY = "documents_translate"
CANONICAL_ROUTE_ID = "documents_translate_canonical_v1"
CANONICAL_ENGINE_ADAPTER = "b13_r18c_documents_translate_v1"

SAFE_DOCUMENT_EXTENSIONS: frozenset[str] = frozenset({
    ".pdf", ".txt", ".docx", ".md", ".srt", ".vtt",
})

SUPPORTED_TARGET_LANGUAGES: frozenset[str] = frozenset({
    "vi", "en", "zh", "ja", "ko", "fr", "de", "es", "ru", "th",
})

DEFAULT_TARGET_LANGUAGE = "vi"
MAX_NOTE_LENGTH = 1000

STATUS_QUEUED = "queued"
STATUS_REASON_AWAITING = "AWAITING_OWNER_AUTHORIZED_RUNTIME_EXECUTION"

FORBIDDEN_AUTHORITY_FIELDS_NORMALIZED: frozenset[str] = frozenset({
    "amount", "amountvnd", "price", "cost", "currency", "paymentid", "ordercode",
    "checkouturl", "webhook", "provider", "providerid", "apikey", "apitoken", "token",
    "secret", "jobid", "jobstatus", "status", "statusreason", "output", "outputurl",
    "assetid", "downloadurl", "role", "balance", "xu", "wallet",
})


def _contains_authority_field(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = "".join(ch for ch in str(key or "").lower() if ch.isalnum())
            if normalized in FORBIDDEN_AUTHORITY_FIELDS_NORMALIZED:
                return True
            if _contains_authority_field(child):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_authority_field(child) for child in value)
    return False


def ensure_document_translate_schema() -> None:
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS web_document_translate_jobs (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                product_key TEXT NOT NULL,
                routing_product_key TEXT NOT NULL,
                document_asset_id TEXT NOT NULL,
                document_name TEXT NOT NULL,
                source_language TEXT NOT NULL,
                target_language TEXT NOT NULL,
                status TEXT NOT NULL,
                status_reason TEXT NOT NULL,
                idempotency_key_hash TEXT,
                payload_hash TEXT NOT NULL,
                bridge_envelope TEXT NOT NULL,
                output_metadata TEXT,
                output_url TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_doc_trans_acct
            ON web_document_translate_jobs (account_id, created_at);
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_doc_trans_req
            ON web_document_translate_jobs (account_id, request_id);
            """
        )


def validate_document_translate_input(
    account_id: str, values: dict[str, Any]
) -> tuple[bool, str, dict[str, Any]]:
    if _contains_authority_field(values):
        return False, "authority_field_not_allowed", {}

    doc_asset_id = str(
        values.get("document_asset_id")
        or values.get("asset_id")
        or values.get("file_id")
        or values.get("document")
        or ""
    ).strip()

    if not doc_asset_id:
        return False, "DOCUMENT_ASSET_REQUIRED", {}

    with read_transaction() as conn:
        row = conn.execute(
            """SELECT id, original_filename, extension, byte_size, state
               FROM web_asset_files
               WHERE id = ? AND account_id = ?""",
            (doc_asset_id, account_id),
        ).fetchone()

        if row is None:
            return False, "DOCUMENT_ASSET_NOT_FOUND_OR_UNAUTHORIZED", {}

        ext = str(row[2] or "").lower()
        if ext not in SAFE_DOCUMENT_EXTENSIONS:
            return False, "INVALID_DOCUMENT_EXTENSION", {}
        doc_name = str(row[1] or doc_asset_id)

    target_lang = str(
        values.get("target_language")
        or values.get("target_lang")
        or values.get("to_lang")
        or DEFAULT_TARGET_LANGUAGE
    ).strip().lower()

    if target_lang not in SUPPORTED_TARGET_LANGUAGES:
        return False, "UNSUPPORTED_TARGET_LANGUAGE", {}

    source_lang = str(
        values.get("source_language")
        or values.get("source_lang")
        or values.get("from_lang")
        or "auto"
    ).strip().lower()

    normalized = {
        "document_asset_id": doc_asset_id,
        "document_name": doc_name,
        "source_language": source_lang,
        "target_language": target_lang,
        "product_key": CANONICAL_PRODUCT_KEY,
        "routing_product_key": CANONICAL_ROUTING_KEY,
    }
    return True, "", normalized


def compute_payload_hash(payload: dict[str, Any]) -> str:
    core = {
        "document_asset_id": str(payload.get("document_asset_id") or "").strip(),
        "product_key": str(payload.get("product_key") or CANONICAL_PRODUCT_KEY),
        "source_language": str(payload.get("source_language") or "auto").strip(),
        "target_language": str(payload.get("target_language") or DEFAULT_TARGET_LANGUAGE).strip(),
    }
    serialized = json.dumps(core, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def compute_idempotency_hash(key: str) -> str:
    cleaned = str(key or "").strip()
    if not cleaned:
        return ""
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()


def generate_canonical_request_id() -> str:
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_part = uuid.uuid4().hex[:6].upper()
    return f"DOC-{date_part}-{random_part}"


def generate_document_translate_job_id() -> str:
    return f"dtj_{uuid.uuid4().hex}"


def _format_public_job(row: tuple, *, idempotent_replay: bool = False) -> dict[str, Any]:
    try:
        env = json.loads(str(row[13])) if row[13] else {}
    except Exception:
        env = {}
    try:
        output_meta = json.loads(str(row[14])) if row[14] else None
    except Exception:
        output_meta = None

    status_str = str(row[9])
    is_completed = status_str == "completed"

    return {
        "id": str(row[0]),
        "request_id": str(row[1]),
        "account_id": str(row[2]),
        "product_key": str(row[3]),
        "routing_product_key": str(row[4]),
        "document_asset_id": str(row[5]),
        "document_name": str(row[6]),
        "source_language": str(row[7]),
        "target_language": str(row[8]),
        "status": status_str,
        "status_reason": str(row[10]),
        "output_available": is_completed,
        "download_ready": is_completed,
        "delivery_ready": is_completed,
        "output": output_meta,
        "output_url": str(row[15]) if len(row) > 15 and row[15] else None,
        "created_at": str(row[16]),
        "updated_at": str(row[17]),
        "bridge_envelope": env,
        "idempotent_replay": idempotent_replay,
    }


def create_or_replay_document_translate_job(
    *,
    account_id: str,
    payload: dict[str, Any],
    request_id: str = "",
    idempotency_key: str = "",
) -> dict[str, Any]:
    """Create a new canonical Document Translate job or replay existing one idempotently."""
    ensure_document_translate_schema()
    owner_id = str(account_id or "").strip()
    if not owner_id:
        raise HTTPException(status_code=401, detail="Xác thực tài khoản Web là bắt buộc")

    is_valid, error_code, normalized = validate_document_translate_input(owner_id, payload)
    if not is_valid:
        error_messages = {
            "authority_field_not_allowed": "Yêu cầu chứa trường authority bị cấm.",
            "DOCUMENT_ASSET_REQUIRED": "Tệp tài liệu từ Asset Vault là bắt buộc đối với Dịch tài liệu.",
            "DOCUMENT_ASSET_NOT_FOUND_OR_UNAUTHORIZED": "Không tìm thấy tệp tài liệu trong Asset Vault của tài khoản hoặc không có quyền truy cập.",
            "INVALID_DOCUMENT_EXTENSION": "Định dạng tài liệu không hợp lệ. Phải thuộc (.pdf, .txt, .docx, .md, .srt, .vtt).",
            "UNSUPPORTED_TARGET_LANGUAGE": f"Ngôn ngữ đích không được hỗ trợ. Phải thuộc {sorted(SUPPORTED_TARGET_LANGUAGES)}.",
        }
        raise HTTPException(status_code=400, detail=error_messages.get(error_code, error_code))

    payload_hash = compute_payload_hash(normalized)
    effective_req_id = str(request_id or payload.get("request_id") or "").strip()
    effective_idem_key = str(idempotency_key or payload.get("idempotency_key") or "").strip()
    idem_hash = compute_idempotency_hash(effective_idem_key) if effective_idem_key else ""

    with transaction() as conn:
        query = """
            SELECT id, request_id, account_id, product_key, routing_product_key,
                   document_asset_id, document_name, source_language, target_language,
                   status, status_reason, idempotency_key_hash, payload_hash,
                   bridge_envelope, output_metadata, output_url, created_at, updated_at
            FROM web_document_translate_jobs
            WHERE account_id = ? AND (
                (? != '' AND request_id = ?)
                OR (? != '' AND idempotency_key_hash = ?)
            )
            ORDER BY created_at DESC LIMIT 1
        """
        row = conn.execute(
            query,
            (owner_id, effective_req_id, effective_req_id, idem_hash, idem_hash),
        ).fetchone()

        if row is not None:
            existing_payload_hash = str(row[12])
            if not hmac.compare_digest(existing_payload_hash, payload_hash):
                raise HTTPException(
                    status_code=409,
                    detail="Xung đột mã yêu cầu: request_id hoặc idempotency_key đã gắn với payload khác.",
                )
            return _format_public_job(row, idempotent_replay=True)

        job_id = generate_document_translate_job_id()
        final_req_id = effective_req_id or generate_canonical_request_id()
        now = utc_now()

        bridge_envelope = {
            "version": "p0.document-translate.canonical-bridge.v1",
            "route_id": CANONICAL_ROUTE_ID,
            "product_family": "documents",
            "mode": "document_translate",
            "engine_adapter": CANONICAL_ENGINE_ADAPTER,
            "product_key": CANONICAL_PRODUCT_KEY,
            "routing_product_key": CANONICAL_ROUTING_KEY,
            "required_capability": "document_translation",
            "document_asset_id": normalized["document_asset_id"],
            "document_name": normalized["document_name"],
            "source_language": normalized["source_language"],
            "target_language": normalized["target_language"],
            "request_id": final_req_id,
            "job_id": job_id,
            "account_id": owner_id,
            "status": STATUS_QUEUED,
            "status_reason": STATUS_REASON_AWAITING,
            "created_at": now,
            "output": None,
        }
        envelope_json = json.dumps(bridge_envelope, ensure_ascii=True, sort_keys=True)

        conn.execute(
            """
            INSERT INTO web_document_translate_jobs (
                id, request_id, account_id, product_key, routing_product_key,
                document_asset_id, document_name, source_language, target_language,
                status, status_reason, idempotency_key_hash, payload_hash,
                bridge_envelope, output_metadata, output_url, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?)
            """,
            (
                job_id,
                final_req_id,
                owner_id,
                CANONICAL_PRODUCT_KEY,
                CANONICAL_ROUTING_KEY,
                normalized["document_asset_id"],
                normalized["document_name"],
                normalized["source_language"],
                normalized["target_language"],
                STATUS_QUEUED,
                STATUS_REASON_AWAITING,
                idem_hash or None,
                payload_hash,
                envelope_json,
                now,
                now,
            ),
        )

        return {
            "id": job_id,
            "request_id": final_req_id,
            "account_id": owner_id,
            "product_key": CANONICAL_PRODUCT_KEY,
            "routing_product_key": CANONICAL_ROUTING_KEY,
            "document_asset_id": normalized["document_asset_id"],
            "document_name": normalized["document_name"],
            "source_language": normalized["source_language"],
            "target_language": normalized["target_language"],
            "status": STATUS_QUEUED,
            "status_reason": STATUS_REASON_AWAITING,
            "output_available": False,
            "download_ready": False,
            "delivery_ready": False,
            "output": None,
            "output_metadata": None,
            "created_at": now,
            "updated_at": now,
            "bridge_envelope": bridge_envelope,
            "idempotent_replay": False,
        }


def get_document_translate_job(account_id: str, job_id: str) -> dict[str, Any] | None:
    ensure_document_translate_schema()
    with read_transaction() as conn:
        row = conn.execute(
            """
            SELECT id, request_id, account_id, product_key, routing_product_key,
                   document_asset_id, document_name, source_language, target_language,
                   status, status_reason, idempotency_key_hash, payload_hash,
                   bridge_envelope, output_metadata, output_url, created_at, updated_at
            FROM web_document_translate_jobs
            WHERE id = ? AND account_id = ?
            """,
            (job_id, account_id),
        ).fetchone()
        if row is None:
            return None
        return _format_public_job(row)


def is_document_translate_job_other_account(job_id: str, account_id: str) -> bool:
    ensure_document_translate_schema()
    with read_transaction() as conn:
        row = conn.execute(
            "SELECT account_id FROM web_document_translate_jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            return False
        return str(row[0]) != str(account_id)


def list_document_translate_jobs(account_id: str, limit: int = 100) -> list[dict[str, Any]]:
    ensure_document_translate_schema()
    safe_limit = max(1, min(limit, 200))
    with read_transaction() as conn:
        rows = conn.execute(
            """
            SELECT id, request_id, account_id, product_key, routing_product_key,
                   document_asset_id, document_name, source_language, target_language,
                   status, status_reason, idempotency_key_hash, payload_hash,
                   bridge_envelope, output_metadata, output_url, created_at, updated_at
            FROM web_document_translate_jobs
            WHERE account_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (account_id, safe_limit),
        ).fetchall()
        return [_format_public_job(row) for row in rows]
