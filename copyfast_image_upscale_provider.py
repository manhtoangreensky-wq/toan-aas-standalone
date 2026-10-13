"""Stability AI Conservative Upscale Provider Adapter.

Task: WEBAPP_R24E1_IMAGE_UPSCALE_PROVIDER_EXECUTOR_FOUNDATION_AND_PROVIDER_FREE_CONTRACT_PROOF_R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Product Family: WebApp / Image Upscale
Provider: Stability AI
Model/Capability: stability_conservative / stability-image-upscale-conservative-v1
Endpoint: https://api.stability.ai/v2beta/stable-image/upscale/conservative

Responsibilities:
1. Provider request construction (multipart/form-data with image stream/bytes, prompt, creativity, output_format).
2. Provider response parsing (binary image stream or JSON with base64, error JSON, task ID extraction).
3. Provider transport boundary (protocol allowing injection of mock/fake transport without network calls).
4. Strictly provider-free execution in tests (REAL_PROVIDER_NETWORK_CALL_COUNT = 0).
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Protocol

# ─── PROVIDER CONTRACT CONSTANTS ─────────────────────────────────────────────

STABILITY_UPSCALE_PROVIDER_NAME: str = "Stability AI"
STABILITY_UPSCALE_PROVIDER_KEY: str = "stability"
STABILITY_UPSCALE_MODEL_NAME: str = "stability_conservative"
STABILITY_UPSCALE_CAPABILITY_ID: str = "stability-image-upscale-conservative-v1"
STABILITY_UPSCALE_ENDPOINT: str = "https://api.stability.ai/v2beta/stable-image/upscale/conservative"

DEFAULT_UPSCALE_PROMPT: str = "high quality, detailed, sharp"
DEFAULT_CREATIVITY: float = 0.35
MIN_CREATIVITY: float = 0.2
MAX_CREATIVITY: float = 0.5
ALLOWED_OUTPUT_FORMATS: frozenset[str] = frozenset({"png", "jpeg", "webp"})
DEFAULT_OUTPUT_FORMAT: str = "png"
MAX_IMAGE_INPUT_BYTES: int = 10 * 1024 * 1024  # 10 MiB official Stability API limit


# Security & Truth Constants (R24E1-FIX1)
PRODUCTION_FAKE_API_KEY_FALLBACK: str = "ABSENT"
MISSING_PROVIDER_CREDENTIAL_BEHAVIOR: str = "FAIL_CLOSED_BEFORE_NETWORK"
SYNTHETIC_PROVIDER_TASK_ID_ALLOWED: bool = False


class ImageUpscaleProviderError(Exception):
    """Base error for image upscale provider operations."""

    def __init__(self, message: str, status_code: int = 500, details: Any = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class ImageUpscaleProviderResponseError(ImageUpscaleProviderError):
    """Raised when provider returns a malformed or invalid response."""

    pass


@dataclass(frozen=True)
class ImageUpscaleProviderRequest:
    job_id: str
    account_id: str
    source_asset_id: str
    image_bytes: bytes
    filename: str
    content_type: str
    scale_factor: int = 2
    prompt: str = DEFAULT_UPSCALE_PROMPT
    creativity: float = DEFAULT_CREATIVITY
    output_format: str = DEFAULT_OUTPUT_FORMAT
    seed: int | None = None


@dataclass(frozen=True)
class ImageUpscaleProviderRawResponse:
    status_code: int
    headers: dict[str, str] = field(default_factory=dict)
    content: bytes = b""
    text: str = ""


@dataclass(frozen=True)
class ImageUpscaleProviderResult:
    provider_task_id: str | None
    provider_name: str
    model_name: str
    output_image_bytes: bytes
    output_content_type: str
    output_extension: str
    finish_reason: str = "SUCCESS"
    output_sha256: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class ImageUpscaleTransportProtocol(Protocol):
    """Transport protocol abstraction for injecting provider-free mock clients."""

    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        files: dict[str, tuple[str, bytes, str]],
        data: dict[str, Any],
    ) -> ImageUpscaleProviderRawResponse:
        ...


def build_stability_upscale_request_payload(
    request: ImageUpscaleProviderRequest,
    api_key: str = "",
) -> tuple[str, dict[str, str], dict[str, tuple[str, bytes, str]], dict[str, Any]]:
    """Constructs the exact HTTP POST payload for Stability AI Conservative Upscale.

    Returns (url, headers, files, data).
    """
    if not request.image_bytes:
        raise ImageUpscaleProviderError("Dữ liệu ảnh đầu vào không được rỗng.", status_code=400)
    if len(request.image_bytes) > MAX_IMAGE_INPUT_BYTES:
        raise ImageUpscaleProviderError(
            f"Dung lượng ảnh vượt quá giới hạn tối đa {MAX_IMAGE_INPUT_BYTES} bytes.",
            status_code=413,
        )

    clean_key = str(api_key).strip()
    if not clean_key:
        raise ImageUpscaleProviderError(
            "Missing provider credential (api_key is required and cannot be empty).",
            status_code=401,
        )

    headers = {
        "Authorization": f"Bearer {clean_key}",
        "Accept": "image/*",
    }

    files = {
        "image": (
            request.filename or "input.png",
            request.image_bytes,
            request.content_type or "image/png",
        ),
    }

    out_fmt = request.output_format.lower() if request.output_format else DEFAULT_OUTPUT_FORMAT
    if out_fmt not in ALLOWED_OUTPUT_FORMATS:
        out_fmt = DEFAULT_OUTPUT_FORMAT

    creativity = float(request.creativity) if request.creativity is not None else DEFAULT_CREATIVITY
    creativity = max(MIN_CREATIVITY, min(MAX_CREATIVITY, creativity))

    data: dict[str, Any] = {
        "prompt": str(request.prompt or DEFAULT_UPSCALE_PROMPT).strip(),
        "output_format": out_fmt,
        "creativity": creativity,
    }
    if request.seed is not None and int(request.seed) >= 0:
        data["seed"] = int(request.seed)

    return STABILITY_UPSCALE_ENDPOINT, headers, files, data


def parse_stability_upscale_response(
    raw: ImageUpscaleProviderRawResponse,
    *,
    job_id: str = "",
) -> ImageUpscaleProviderResult:
    """Parses Stability AI Upscale response into a verified ImageUpscaleProviderResult.

    Enforces:
    - Status 200 OK.
    - Handles binary image/* or JSON base64 payloads.
    - Fails closed on malformed, corrupt, or non-200 responses.
    - Extracts provider task ID from headers (x-request-id / x-stability-request-id).
    - SYNTHETIC_PROVIDER_TASK_ID_ALLOWED = False (leaves None if header is absent).
    - Truthful finish_reason parsing (non-SUCCESS fails closed).
    """
    if raw.status_code != 200:
        error_msg = f"Provider returned HTTP {raw.status_code}"
        details: dict[str, Any] = {}
        if raw.text:
            try:
                err_json = json.loads(raw.text)
                if isinstance(err_json, dict):
                    details = err_json
                    errs = err_json.get("errors")
                    if isinstance(errs, list) and errs:
                        error_msg = f"Provider error: {'; '.join(str(e) for e in errs)}"
                    elif "message" in err_json:
                        error_msg = f"Provider error: {err_json['message']}"
            except Exception:
                error_msg = f"Provider error ({raw.status_code}): {raw.text[:200]}"
        raise ImageUpscaleProviderError(error_msg, status_code=raw.status_code, details=details)

    if not raw.content and not raw.text:
        raise ImageUpscaleProviderResponseError(
            "Malformed provider response: empty response body.", status_code=502
        )

    content_type = raw.headers.get("content-type", "").lower()
    raw_task_id = raw.headers.get("x-request-id") or raw.headers.get("x-stability-request-id")
    task_id = str(raw_task_id).strip() if raw_task_id else None

    # Case A: Binary image payload
    is_binary_image = (
        "image/" in content_type
        or (raw.content and raw.content[:8] == b"\x89PNG\r\n\x1a\n")
        or (raw.content and raw.content[:2] == b"\xff\xd8")
    )
    if is_binary_image:
        output_bytes = raw.content
        if not output_bytes or len(output_bytes) < 16:
            raise ImageUpscaleProviderResponseError(
                "Malformed provider response: image binary corrupted or empty.",
                status_code=502,
            )

        finish_reason_hdr = raw.headers.get("finish-reason") or raw.headers.get("x-finish-reason")
        finish_reason = str(finish_reason_hdr).strip() if finish_reason_hdr else "SUCCESS"
        if finish_reason.upper() != "SUCCESS":
            raise ImageUpscaleProviderResponseError(
                f"Provider returned non-success finish-reason: {finish_reason}",
                status_code=502,
            )

        if "jpeg" in content_type or "jpg" in content_type or output_bytes[:2] == b"\xff\xd8":
            ext = ".jpg"
            mime = "image/jpeg"
        elif "webp" in content_type or output_bytes[:4] == b"RIFF":
            ext = ".webp"
            mime = "image/webp"
        else:
            ext = ".png"
            mime = "image/png"

        output_sha256 = hashlib.sha256(output_bytes).hexdigest()

        return ImageUpscaleProviderResult(
            provider_task_id=task_id,
            provider_name=STABILITY_UPSCALE_PROVIDER_KEY,
            model_name=STABILITY_UPSCALE_MODEL_NAME,
            output_image_bytes=output_bytes,
            output_content_type=mime,
            output_extension=ext,
            finish_reason=finish_reason,
            output_sha256=output_sha256,
            metadata={
                "content_length": len(output_bytes),
                "task_id": task_id,
                "output_sha256": output_sha256,
                "finish_reason": finish_reason,
            },
        )

    # Case B: JSON payload with base64
    is_json = "json" in content_type or (raw.text and raw.text.strip().startswith("{"))
    if is_json:
        try:
            body = json.loads(raw.text or raw.content.decode("utf-8"))
        except Exception as exc:
            raise ImageUpscaleProviderResponseError(
                f"Malformed provider response: invalid JSON ({exc})", status_code=502
            ) from exc

        if not isinstance(body, dict) or "image" not in body:
            raise ImageUpscaleProviderResponseError(
                "Malformed provider response: missing 'image' field in JSON response.",
                status_code=502,
            )

        try:
            output_bytes = base64.b64decode(body["image"])
        except Exception as exc:
            raise ImageUpscaleProviderResponseError(
                f"Malformed provider response: invalid base64 image data ({exc})",
                status_code=502,
            ) from exc

        if not output_bytes or len(output_bytes) < 16:
            raise ImageUpscaleProviderResponseError(
                "Malformed provider response: decoded image bytes empty or corrupt.",
                status_code=502,
            )

        finish_reason = str(body.get("finish_reason") or raw.headers.get("finish-reason") or "SUCCESS").strip()
        if finish_reason.upper() != "SUCCESS":
            raise ImageUpscaleProviderResponseError(
                f"Provider returned non-success finish-reason: {finish_reason}",
                status_code=502,
            )

        output_sha256 = hashlib.sha256(output_bytes).hexdigest()
        seed = body.get("seed")

        return ImageUpscaleProviderResult(
            provider_task_id=task_id,
            provider_name=STABILITY_UPSCALE_PROVIDER_KEY,
            model_name=STABILITY_UPSCALE_MODEL_NAME,
            output_image_bytes=output_bytes,
            output_content_type="image/png",
            output_extension=".png",
            finish_reason=finish_reason,
            output_sha256=output_sha256,
            metadata={
                "seed": seed,
                "finish_reason": finish_reason,
                "task_id": task_id,
                "output_sha256": output_sha256,
            },
        )

    raise ImageUpscaleProviderResponseError(
        f"Malformed provider response: unsupported content-type '{content_type}'.",
        status_code=502,
    )


class FakeStabilityUpscaleTransport(ImageUpscaleTransportProtocol):
    """Deterministic, provider-free mock transport for test execution.

    Tracks call counts, inspected headers and payloads, and returns configurable raw responses.
    Ensures REAL_PROVIDER_NETWORK_CALL_COUNT = 0.
    """

    def __init__(
        self,
        *,
        status_code: int = 200,
        response_image_bytes: bytes | None = None,
        response_json: dict[str, Any] | None = None,
        error_text: str = "",
        headers: dict[str, str] | None = None,
        include_request_id: bool = True,
    ):
        self.call_count: int = 0
        self.recorded_requests: list[dict[str, Any]] = []
        self.status_code = status_code
        self.include_request_id = include_request_id
        # Minimal valid 2x2 PNG for mock delivery
        self.response_image_bytes = (
            response_image_bytes
            if response_image_bytes is not None
            else b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x02\x00\x00\x00\x02\x08\x06\x00\x00\x00\xf4x\xd4\xfa\x00\x00\x00\x10IDATx\x9cc\xfc\xff\xff?\x03\x00\x08\xfc\x02\xfe\xa7\x9a\xa0\xa0\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        self.response_json = response_json
        self.error_text = error_text
        self.custom_headers = headers or {}

    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        files: dict[str, tuple[str, bytes, str]],
        data: dict[str, Any],
    ) -> ImageUpscaleProviderRawResponse:
        self.call_count += 1
        self.recorded_requests.append({
            "url": url,
            "headers": dict(headers),
            "files": {k: (v[0], len(v[1]), v[2]) for k, v in files.items()},
            "data": dict(data),
        })

        resp_headers = {
            "content-type": "image/png",
        }
        if self.include_request_id:
            resp_headers["x-request-id"] = f"fake_task_{self.call_count}"
        resp_headers.update(self.custom_headers)

        if self.status_code != 200:
            return ImageUpscaleProviderRawResponse(
                status_code=self.status_code,
                headers=resp_headers,
                text=self.error_text or json.dumps({"errors": ["Mock provider error"]}),
                content=b"",
            )

        if self.response_json is not None:
            resp_headers["content-type"] = "application/json"
            return ImageUpscaleProviderRawResponse(
                status_code=200,
                headers=resp_headers,
                text=json.dumps(self.response_json),
                content=json.dumps(self.response_json).encode("utf-8"),
            )

        return ImageUpscaleProviderRawResponse(
            status_code=200,
            headers=resp_headers,
            content=self.response_image_bytes,
            text="",
        )
