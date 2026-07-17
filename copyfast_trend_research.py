"""Private, deterministic Trend Research planning for the standalone Web App.

The frozen Telegram Bot's ``/trend_research`` command is a compact manual
research checklist, not a live search engine.  This Web-native translation
keeps its useful keyword, selection and originality guidance while adding a
strict signed-session/CSRF boundary.  It deliberately never calls TikTok,
YouTube, Facebook, Google Trends, a provider, the Bot/Core Bridge, a job,
wallet, PayOS, Asset Vault, publisher or any remote URL.
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, StrictStr, field_validator

from copyfast_auth import envelope, require_csrf
from copyfast_db import trend_research_enabled


router = APIRouter(prefix="/api/v1/trend-research", tags=["Web Trend Research"])

LANGUAGES = frozenset({"vi", "en"})
TOPIC_MAX_LENGTH = 180
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

# Only clearly harmful execution/copyright-evasion prompts are guarded. A
# neutral topic such as "phòng chống deepfake" remains researchable; this
# surface never verifies claims, rights or trend freshness either way.
POLICY_GUARD_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:reup|re-upload|reupload|tải\s*(?:lại|video)|download\s+(?:video|content)).{0,80}\b(?:không\s*có\s*quyền|without\s+(?:permission|rights)|của\s*người\s*khác)", re.IGNORECASE),
    re.compile(r"\b(?:né|bypass|remove|xóa|xoá|vượt)\s*(?:watermark|drm|content\s*id)\b|\b(?:watermark|drm|content\s*id)\s*(?:bypass|removal|remover)\b", re.IGNORECASE),
    re.compile(r"\b(?:mạo\s*danh|impersonat(?:e|ion)|nhái\s*giọng|clone\s*giọng|voice\s*clone|giả\s*mạo\s*người)\b", re.IGNORECASE),
    re.compile(r"\b(?:tạo|làm|make|create|generate)\s+(?:một\s+)?deepfake\b|\bdeepfake\s+(?:của|người|person|celebrity|real)\b", re.IGNORECASE),
)


def _require_enabled() -> None:
    if not trend_research_enabled():
        raise HTTPException(
            status_code=503,
            detail="Trend Research đang tạm dừng để bảo trì. WEBAPP_TREND_RESEARCH_ENABLED chưa được bật.",
        )


def _sensitive(value: str) -> bool:
    return bool(
        SECRET_ASSIGNMENT_PATTERN.search(value)
        or KNOWN_SECRET_PATTERN.search(value)
        or CARD_LIKE_PATTERN.search(value)
        or OTP_PATTERN.search(value)
    )


def _topic(value: str) -> str:
    if "\r" in value or "\n" in value:
        raise ValueError("Chủ đề Trend Research phải nằm trên một dòng")
    normalized = re.sub(r"\s+", " ", value).strip()
    if UNSAFE_CONTROL_PATTERN.search(normalized) or not 2 <= len(normalized) <= TOPIC_MAX_LENGTH:
        raise ValueError(f"Chủ đề cần từ 2 đến {TOPIC_MAX_LENGTH} ký tự hợp lệ")
    if MARKUP_PATTERN.search(normalized) or URL_OR_PATH_PATTERN.search(normalized) or SOCIAL_HANDLE_PATTERN.search(normalized):
        raise ValueError("Chủ đề không nhận markup, URL, path, tệp hoặc social handle")
    if _sensitive(normalized):
        raise ValueError("Chủ đề không nhận secret, token, OTP hoặc dữ liệu thẻ")
    return normalized


class TrendResearchRequest(BaseModel):
    """Exact request contract for a transient manual research plan.

    There is intentionally no source URL, platform credential, time range,
    asset, project, provider/model selector, job, idempotency, payment or
    publish field. The browser sends only the topic and display language.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    topic: StrictStr
    language: StrictStr = "vi"

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: str) -> str:
        return _topic(value)

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        language = str(value).strip().lower()
        if language not in LANGUAGES:
            raise ValueError("Ngôn ngữ Trend Research chỉ hỗ trợ vi hoặc en")
        return language


def _boundary() -> dict[str, Any]:
    """Complete no-execution boundary, validated by Portal before rendering."""

    return {
        "execution": "web_native_deterministic_trend_research_only",
        "input_persisted": False,
        "live_search_called": False,
        "search_provider_called": False,
        "social_platform_called": False,
        "source_content_fetched": False,
        "source_content_stored": False,
        "provider_called": False,
        "bot_called": False,
        "job_created": False,
        "wallet_mutated": False,
        "payment_started": False,
        "asset_saved": False,
        "media_output_created": False,
        "publish_action_created": False,
        "fact_checked": False,
        "trend_claim_verified": False,
        "rights_verified": False,
    }


def _policy_guard(topic: str) -> dict[str, Any] | None:
    if not any(pattern.search(topic) for pattern in POLICY_GUARD_PATTERNS):
        return None
    return envelope(
        False,
        "Chủ đề cần được viết lại theo hướng nghiên cứu và sáng tạo nguyên bản, không reup/copy không có quyền, né watermark/DRM/Content ID, mạo danh, clone hoặc deepfake người thật.",
        data=_boundary(),
        status_name="guarded",
        error_code="WEB_TREND_RESEARCH_POLICY_GUARD",
    )


def _query_suffixes(language: str) -> tuple[str, str, str, str]:
    if language == "en":
        return ("review", "common mistakes", "before buying", "time-saving tips")
    return ("review", "lỗi thường gặp", "trước khi mua", "mẹo tiết kiệm thời gian")


def _compose_plan(payload: TrendResearchRequest) -> dict[str, Any]:
    """Translate Bot's five-keyword checklist into an editable Web receipt."""

    topic = payload.topic
    review, mistakes, before_buying, time_saving = _query_suffixes(payload.language)
    queries = [topic, f"{topic} {review}", f"{topic} {mistakes}", f"{topic} {before_buying}", f"{topic} {time_saving}"]
    if payload.language == "en":
        title = f"Manual trend research plan: {topic}"
        selection_criteria = [
            "Prioritize topics with many recently published videos after you inspect them manually.",
            "Notice hooks or framing that recur across independent creators.",
            "Look for comments that express a concrete need, confusion or decision point.",
            "Choose an angle that can become your own original content rather than a copy.",
            "Exclude ideas that depend on reuploading or copying the original work.",
        ]
        review_before_use = [
            "This is a manual keyword checklist, not live, recent or verified trend data.",
            "Open and assess sources yourself; verify facts, dates, claims and local relevance before publishing.",
            "Confirm rights for every reference, person, brand, asset and source you decide to use.",
        ]
    else:
        title = f"Kế hoạch nghiên cứu trend thủ công: {topic}"
        selection_criteria = [
            "Ưu tiên chủ đề có nhiều video mới gần đây sau khi bạn tự kiểm tra thủ công.",
            "Quan sát hook hoặc cách đóng khung lặp lại giữa các creator độc lập.",
            "Tìm comment thể hiện nhu cầu, băn khoăn hoặc điểm ra quyết định thật.",
            "Chọn góc có thể chuyển thành nội dung nguyên bản của riêng bạn, không sao chép.",
            "Loại bỏ ý tưởng phụ thuộc vào reup hoặc copy nguyên bản.",
        ]
        review_before_use = [
            "Đây là checklist keyword thủ công, không phải dữ liệu trend live, mới nhất hoặc đã xác minh.",
            "Tự mở và đánh giá nguồn; kiểm chứng fact, ngày tháng, claim và mức phù hợp trước khi publish.",
            "Xác nhận quyền sử dụng cho mọi reference, người, thương hiệu, asset và nguồn bạn chọn dùng.",
        ]
    return {
        "title": title,
        "topic": topic,
        "language": payload.language,
        "research_mode": "manual_content_only",
        "freshness": "not_live_not_verified",
        "keyword_groups": [
            {"surface": "TikTok Search", "queries": queries},
            {"surface": "YouTube Shorts", "queries": queries},
            {"surface": "Facebook Reels", "queries": queries},
            {"surface": "Google Trends", "queries": [topic]},
            {"surface": "Cộng đồng phù hợp", "queries": [topic]},
        ],
        "selection_criteria": selection_criteria,
        "originality_guardrails": [
            "Không tải hoặc reup nội dung khi chưa có quyền sử dụng rõ ràng.",
            "Không né watermark, DRM hoặc Content ID.",
            "Không dùng giọng, hình hoặc danh tính người thật khi chưa có quyền hợp lệ.",
            "Tạo script, hình, voice và video mới từ insight; không sao chép tác phẩm nguồn.",
        ],
        "next_workflows": [
            {"label": "Content Prompt Pack", "route": "/content/prompt-pack", "purpose": "Chuyển insight đã tự kiểm tra thành khung nội dung text."},
            {"label": "Image Prompt Composer", "route": "/image/prompt-composer", "purpose": "Soạn hướng visual nguyên bản để review."},
            {"label": "Video Prompt Planner", "route": "/video-studio/prompt-planner", "purpose": "Lập kế hoạch video text-only trước khi chọn engine riêng."},
        ],
        "review_before_use": review_before_use,
    }


@router.post("/plan")
async def create_trend_research_plan(
    payload: TrendResearchRequest,
    account: dict = Depends(require_csrf),
):
    """Return a request-only, deterministic manual research checklist.

    The signed session and CSRF proof protect the private portal route, but
    no account-specific state is read or written. In particular, do not add
    audit detail, database storage, request receipts, bot/bridge dispatch,
    live search, social scraping, provider/model work, job, wallet, payment,
    asset, media, publish or delivery code to this endpoint.
    """

    _require_enabled()
    del account
    guarded = _policy_guard(payload.topic)
    if guarded:
        return guarded
    return envelope(
        True,
        "Đã tạo checklist nghiên cứu trend thủ công để bạn tự kiểm tra. Không có live search, nguồn external, Bot, provider, job, thanh toán hoặc nội dung media được tạo.",
        data={"plan": _compose_plan(payload), **_boundary()},
        status_name="draft",
    )
