"""Signed, deterministic Prompt Blueprint Composer for the Web App.

The frozen Telegram Bot has several prompt-planning conversations, but their
pending state, provider/model choices, Xu, jobs and delivery belong to the
Bot.  This module intentionally owns none of those concerns.  It turns a
small, sanitized editorial brief into a copyable *blueprint* only: a human can
review or manually move it to the separate Prompt Library afterwards.

No request is persisted here.  In particular, this router never imports Bot or
Core Bridge code, writes a Prompt Library template, starts a model/provider,
creates a job, changes wallet/PayOS state, stores an asset, or publishes
anything.
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator

from copyfast_auth import envelope, require_account, require_csrf
from copyfast_db import prompt_studio_enabled


router = APIRouter(prefix="/api/v1/prompt-studio", tags=["Web Prompt Blueprint Composer"])

LANGUAGES = frozenset({"vi", "en"})
PLATFORMS = frozenset({"general", "chat", "social", "website", "email", "image", "video", "voice", "document"})
TONES = frozenset({"clear", "friendly", "professional", "persuasive", "educational", "creative", "neutral"})
OUTPUT_FORMATS = frozenset({"general", "content", "caption", "script", "image_prompt", "video_prompt", "voice_script", "document_outline"})

MAX_GOAL = 300
MAX_AUDIENCE = 300
MAX_CONSTRAINTS = 1_200
UNSAFE_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
MARKUP_PATTERN = re.compile(
    r"(?:<\s*/?\s*[A-Za-z][^>\r\n]{0,240}>|\[[^\]\r\n]{1,160}\]\([^\)\r\n]{1,480}\)|```|\bon[a-z]+\s*=)",
    re.IGNORECASE,
)
URL_OR_PATH_PATTERN = re.compile(
    r"(?:\b(?:https?|ftp)://|\bwww\.|\b(?:file|data|javascript|tg):|(?:^|\s)[A-Za-z]:[\\/]|(?:^|\s)/(?:[A-Za-z0-9_.-]+/){1,})",
    re.IGNORECASE,
)
SOCIAL_HANDLE_PATTERN = re.compile(r"(?:^|\s)@[A-Za-z0-9_]{3,}")
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|token|"
    r"client[ _-]?secret|secret(?:[ _-]?(?:key|access[ _-]?key))?|password|passphrase|authorization)\b\s*"
    r"(?:['\"]\s*)?(?:[:=]|\bis\b)\s*(?:['\"]\s*)?(?:(?:bearer|basic)\s+)?[A-Za-z0-9_./+=:-]{8,}",
    re.IGNORECASE,
)
KNOWN_SECRET_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(?:(?:sk|pk|rk)[_-][A-Za-z0-9_-]{12,}|gh(?:p|o|u|s|r)_[A-Za-z0-9]{12,}|"
    r"github_pat_[A-Za-z0-9_]{12,}|xox(?:b|p|a|r|s)-[A-Za-z0-9-]{12,}|AIza[0-9A-Za-z_-]{20,}|"
    r"(?:AKIA|ASIA)[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,})(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
CARD_LIKE_PATTERN = re.compile(r"(?<![0-9A-Za-z])[0-9](?:[\s./-]*[0-9]){12,18}(?![0-9A-Za-z])")
OTP_PATTERN = re.compile(
    r"\b(?:otp|cvv|cvc|pin|mã\s*(?:xác\s*(?:minh|thực)|otp)|ma\s*(?:xac\s*(?:minh|thuc)|otp)|"
    r"verification\s+(?:code|token)|one[ -]?time(?:\s+(?:pass(?:word|code)?|code))?)\b",
    re.IGNORECASE,
)

# This is a planning surface, not an imitation/copyright-evasion helper.  The
# guard is intentionally narrow enough to leave normal compliance discussion
# (for example "how to avoid deepfakes") available as an editorial topic.
POLICY_GUARD_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:mạo\s*danh|impersonat(?:e|ion)|nhái\s*giọng|clone\s*giọng|voice\s*clone|giả\s*mạo\s*người)\b", re.IGNORECASE),
    re.compile(r"\b(?:tạo|làm|make|create|generate)\s+(?:một\s+)?deepfake\b|\bdeepfake\s+(?:của|người|person|celebrity|real)\b", re.IGNORECASE),
    re.compile(r"\b(?:reup|re-upload|reupload|tải\s*(?:lại|video)|download\s+(?:video|content)).{0,80}\b(?:không\s*có\s*quyền|without\s+(?:permission|rights)|của\s*người\s*khác)", re.IGNORECASE),
    re.compile(r"\b(?:né|bypass|remove|xóa|xoá|vượt)\s*(?:watermark|drm|content\s*id)\b|\b(?:watermark|drm|content\s*id)\s*(?:bypass|removal|remover)\b", re.IGNORECASE),
)


def _require_enabled() -> None:
    if not prompt_studio_enabled():
        raise HTTPException(
            status_code=503,
            detail="Prompt Studio đang tạm dừng để bảo trì. WEBAPP_PROMPT_STUDIO_ENABLED chưa được bật.",
        )


def _sensitive(value: str) -> bool:
    return bool(
        SECRET_ASSIGNMENT_PATTERN.search(value)
        or KNOWN_SECRET_PATTERN.search(value)
        or CARD_LIKE_PATTERN.search(value)
        or OTP_PATTERN.search(value)
    )


def _text(value: str, *, label: str, minimum: int, maximum: int, allow_empty: bool = False) -> str:
    """Accept only concise editorial text, never executable/reference data."""

    if "\r" in value or "\n" in value:
        raise ValueError(f"{label} phải nằm trên một dòng")
    normalized = re.sub(r"\s+", " ", value).strip()
    if UNSAFE_CONTROL_PATTERN.search(normalized) or len(normalized) > maximum or (not allow_empty and len(normalized) < minimum):
        if allow_empty:
            raise ValueError(f"{label} tối đa {maximum} ký tự hợp lệ")
        raise ValueError(f"{label} cần từ {minimum} đến {maximum} ký tự hợp lệ")
    if normalized and (MARKUP_PATTERN.search(normalized) or URL_OR_PATH_PATTERN.search(normalized) or SOCIAL_HANDLE_PATTERN.search(normalized)):
        raise ValueError(f"{label} không nhận markup, URL, path, tệp hoặc social handle")
    if normalized and _sensitive(normalized):
        raise ValueError(f"{label} không nhận secret, token, OTP hoặc dữ liệu thẻ")
    return normalized


class PromptBlueprintRequest(BaseModel):
    """Exact request contract for a non-persistent editorial blueprint.

    There is deliberately no account id, template id, URL, file, provider or
    model selector, source asset, job, payment, quote, publish or delivery
    field.  A future explicit Prompt Library handoff must re-compute server
    material and have its own idempotent write contract; it does not belong in
    this transient endpoint.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    goal: StrictStr
    audience: StrictStr = ""
    platform: StrictStr = "general"
    tone: StrictStr = "clear"
    language: StrictStr = "vi"
    output_format: StrictStr = "general"
    constraints: StrictStr = ""

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, value: str) -> str:
        return _text(value, label="Mục tiêu", minimum=2, maximum=MAX_GOAL)

    @field_validator("audience")
    @classmethod
    def validate_audience(cls, value: str) -> str:
        return _text(value, label="Đối tượng", minimum=0, maximum=MAX_AUDIENCE, allow_empty=True)

    @field_validator("constraints")
    @classmethod
    def validate_constraints(cls, value: str) -> str:
        return _text(value, label="Ràng buộc", minimum=0, maximum=MAX_CONSTRAINTS, allow_empty=True)

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, value: str) -> str:
        normalized = str(value).strip().lower()
        if normalized not in PLATFORMS:
            raise ValueError("Nền tảng Prompt Studio không hợp lệ")
        return normalized

    @field_validator("tone")
    @classmethod
    def validate_tone(cls, value: str) -> str:
        normalized = str(value).strip().lower()
        if normalized not in TONES:
            raise ValueError("Tone Prompt Studio không hợp lệ")
        return normalized

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        normalized = str(value).strip().lower()
        if normalized not in LANGUAGES:
            raise ValueError("Ngôn ngữ Prompt Studio chỉ hỗ trợ vi hoặc en")
        return normalized

    @field_validator("output_format")
    @classmethod
    def validate_output_format(cls, value: str) -> str:
        normalized = str(value).strip().lower()
        if normalized not in OUTPUT_FORMATS:
            raise ValueError("Định dạng đầu ra Prompt Studio không hợp lệ")
        return normalized


class PromptBlueprintVariable(BaseModel):
    """Display-only schema for a copyable prompt variable."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=160)
    required: bool


class PromptBlueprint(BaseModel):
    """Bounded, deterministic output; this is never a model/provider result."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=320)
    goal: str = Field(min_length=2, max_length=MAX_GOAL)
    audience: str = Field(max_length=MAX_AUDIENCE)
    platform: str
    tone: str
    language: str
    output_format: str
    prompt_text: str = Field(min_length=1, max_length=8_000)
    negative_prompt: str = Field(min_length=1, max_length=3_000)
    variables: list[PromptBlueprintVariable] = Field(min_length=2, max_length=8)
    review_checklist: list[str] = Field(min_length=4, max_length=8)


PLATFORM_LABELS = {
    "general": {"vi": "môi trường chung", "en": "a general context"},
    "chat": {"vi": "hội thoại", "en": "a conversation"},
    "social": {"vi": "nội dung mạng xã hội", "en": "social content"},
    "website": {"vi": "website", "en": "a website"},
    "email": {"vi": "email", "en": "email"},
    "image": {"vi": "brief hình ảnh", "en": "an image brief"},
    "video": {"vi": "brief video", "en": "a video brief"},
    "voice": {"vi": "lời thoại", "en": "a voice script"},
    "document": {"vi": "tài liệu", "en": "a document"},
}
TONE_LABELS = {
    "clear": {"vi": "rõ ràng", "en": "clear"},
    "friendly": {"vi": "thân thiện", "en": "friendly"},
    "professional": {"vi": "chuyên nghiệp", "en": "professional"},
    "persuasive": {"vi": "thuyết phục có kiểm soát", "en": "measured and persuasive"},
    "educational": {"vi": "giải thích dễ hiểu", "en": "educational"},
    "creative": {"vi": "sáng tạo nhưng cụ thể", "en": "creative but concrete"},
    "neutral": {"vi": "trung tính", "en": "neutral"},
}
OUTPUT_LABELS = {
    "general": {"vi": "bản nháp có cấu trúc", "en": "a structured draft"},
    "content": {"vi": "nội dung", "en": "content"},
    "caption": {"vi": "caption", "en": "a caption"},
    "script": {"vi": "kịch bản", "en": "a script"},
    "image_prompt": {"vi": "prompt ảnh", "en": "an image prompt"},
    "video_prompt": {"vi": "prompt video", "en": "a video prompt"},
    "voice_script": {"vi": "lời thoại", "en": "a voice script"},
    "document_outline": {"vi": "dàn ý tài liệu", "en": "a document outline"},
}


def _boundary() -> dict[str, Any]:
    """Complete no-execution contract used for every endpoint outcome."""

    return {
        "execution": "web_native_deterministic_prompt_blueprint_only",
        "input_persisted": False,
        "template_persisted": False,
        "bot_called": False,
        "bridge_called": False,
        "provider_called": False,
        "job_created": False,
        "wallet_mutated": False,
        "payment_started": False,
        "asset_saved": False,
        "media_output_created": False,
        "publish_action_created": False,
        "delivery_created": False,
        "fact_checked": False,
        "rights_verified": False,
    }


def _policy_guard(payload: PromptBlueprintRequest) -> dict[str, Any] | None:
    text = "\n".join((payload.goal, payload.audience, payload.constraints))
    if not any(pattern.search(text) for pattern in POLICY_GUARD_PATTERNS):
        return None
    return envelope(
        False,
        "Brief cần được viết lại theo hướng nguyên bản và không mạo danh, clone/deepfake người thật, reup/copy không có quyền hoặc né watermark/DRM/Content ID.",
        data=_boundary(),
        status_name="guarded",
        error_code="WEB_PROMPT_STUDIO_POLICY_GUARD",
    )


def _variable_schema(language: str, *, audience_given: bool, constraints_given: bool) -> list[dict[str, Any]]:
    if language == "en":
        entries = [
            ("goal", "Editorial goal", True),
            ("audience", "Audience context", not audience_given),
            ("constraints", "Constraints to preserve", not constraints_given),
            ("facts_to_verify", "Facts, prices, dates, and claims to verify", True),
        ]
    else:
        entries = [
            ("goal", "Mục tiêu biên tập", True),
            ("audience", "Ngữ cảnh đối tượng", not audience_given),
            ("constraints", "Ràng buộc cần giữ", not constraints_given),
            ("facts_to_verify", "Fact, giá, ngày tháng và claim cần kiểm tra", True),
        ]
    return [PromptBlueprintVariable(name=name, label=label, required=required).model_dump() for name, label, required in entries]


def _compose_blueprint(payload: PromptBlueprintRequest) -> dict[str, Any]:
    """Create a readable deterministic blueprint from bounded editorial data."""

    language = payload.language
    platform = PLATFORM_LABELS[payload.platform][language]
    tone = TONE_LABELS[payload.tone][language]
    output = OUTPUT_LABELS[payload.output_format][language]
    audience = payload.audience or ("đối tượng do người dùng xác định" if language == "vi" else "the audience defined by the user")
    constraints = payload.constraints or ("không có ràng buộc bổ sung" if language == "vi" else "no additional constraints supplied")
    if language == "en":
        title = f"Prompt blueprint: {payload.goal}"
        prompt_text = (
            f"Act as an editorial assistant. Create {output} for {platform}.\n\n"
            f"Goal: {payload.goal}\nAudience: {audience}\nTone: {tone}\nConstraints: {constraints}\n\n"
            "Return:\n"
            "1. A concise working draft that directly serves the goal.\n"
            "2. A short structure or sequence that a human can revise.\n"
            "3. A clear CTA or next editorial action when relevant.\n"
            "4. A list of factual, rights, or brand-sensitive items to verify.\n\n"
            "Use only information supplied in this brief. Mark missing facts as [verify] instead of inventing them."
        )
        negative_prompt = (
            "Do not invent prices, dates, availability, outcomes, testimonials, legal claims, or source rights. "
            "Do not imitate a real person or protected creator, copy a source work, request credentials, or imply publishing/execution."
        )
        checklist = [
            "Check every fact, price, date, statistic, and comparison before external use.",
            "Confirm rights for brands, people, assets, music, images, and references.",
            "Remove sensitive data, secrets, credentials, payment evidence, and private identifiers.",
            "Review tone, audience fit, accessibility, and platform rules before using the draft elsewhere.",
        ]
    else:
        title = f"Prompt blueprint: {payload.goal}"
        prompt_text = (
            f"Bạn là trợ lý biên tập. Hãy tạo {output} cho {platform}.\n\n"
            f"Mục tiêu: {payload.goal}\nĐối tượng: {audience}\nGiọng điệu: {tone}\nRàng buộc: {constraints}\n\n"
            "Trả theo cấu trúc:\n"
            "1. Bản nháp ngắn, trực tiếp phục vụ mục tiêu.\n"
            "2. Dàn ý hoặc trình tự để người biên tập tiếp tục chỉnh.\n"
            "3. CTA hoặc bước biên tập tiếp theo khi phù hợp.\n"
            "4. Danh sách fact, quyền hoặc điểm nhạy cảm thương hiệu cần tự kiểm tra.\n\n"
            "Chỉ dùng thông tin trong brief. Đánh dấu [cần kiểm tra] cho dữ kiện còn thiếu, không tự bịa thêm."
        )
        negative_prompt = (
            "Không bịa giá, ngày tháng, mức sẵn có, kết quả, testimonial, tuyên bố pháp lý hoặc quyền sử dụng nguồn. "
            "Không mạo danh người thật/creator, sao chép tác phẩm nguồn, yêu cầu credential, hoặc ngụ ý đã đăng hay đã thực thi."
        )
        checklist = [
            "Kiểm tra mọi fact, giá, ngày tháng, số liệu và so sánh trước khi dùng bên ngoài.",
            "Xác nhận quyền với thương hiệu, người xuất hiện, asset, nhạc, hình ảnh và tư liệu tham chiếu.",
            "Loại bỏ dữ liệu nhạy cảm, secret, credential, chứng từ thanh toán và định danh riêng tư.",
            "Rà soát tone, mức phù hợp với đối tượng, accessibility và chính sách kênh trước khi dùng bản nháp ở nơi khác.",
        ]
    result = {
        "title": title,
        "goal": payload.goal,
        "audience": payload.audience,
        "platform": payload.platform,
        "tone": payload.tone,
        "language": payload.language,
        "output_format": payload.output_format,
        "prompt_text": prompt_text,
        "negative_prompt": negative_prompt,
        "variables": _variable_schema(language, audience_given=bool(payload.audience), constraints_given=bool(payload.constraints)),
        "review_checklist": checklist,
    }
    return PromptBlueprint.model_validate(result).model_dump()


@router.get("/policy")
async def prompt_studio_policy(account: dict = Depends(require_account)):
    """Expose only a small static policy for the signed Web shell."""

    _require_enabled()
    del account
    return envelope(
        True,
        "Prompt Studio chỉ tạo blueprint text deterministic để bạn tự review; không tạo template, AI output hay tác vụ thực thi.",
        data={
            "feature": "prompt_blueprint_composer",
            "platforms": sorted(PLATFORMS),
            "tones": sorted(TONES),
            "languages": sorted(LANGUAGES),
            "output_formats": sorted(OUTPUT_FORMATS),
            **_boundary(),
        },
        status_name="ready",
    )


@router.post("/compose")
async def compose_prompt_blueprint(payload: PromptBlueprintRequest, account: dict = Depends(require_csrf)):
    """Return one transient, deterministic prompt blueprint.

    The signed session and CSRF token protect the private authoring route, but
    no account state is read or written.  Do not add an implicit save, audit
    detail, Bot/Core Bridge call, provider/model request, job, wallet/payment
    mutation, asset, publish action, delivery, browser-storage contract, or
    any claim that this text is a generated model result.
    """

    _require_enabled()
    del account
    guarded = _policy_guard(payload)
    if guarded:
        return guarded
    return envelope(
        True,
        "Đã tạo Prompt Blueprint để bạn copy và tự review. Không có template được lưu, AI/provider/Bot, job, Xu, PayOS, asset, publish hay delivery nào được tạo.",
        data={"blueprint": _compose_blueprint(payload), **_boundary()},
        status_name="draft",
    )
