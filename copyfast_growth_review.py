"""Private, deterministic Growth Review for the standalone Web App.

The historical Telegram Bot has a small, useful performance-score helper and
a fixed recommendation tree.  Its real ``/growth_ai`` conversation also owns
live/canonical analytics, model calls, Xu and refund behaviour, so that part
must remain outside this independent Web surface.  This router translates
only the pure local rule set into a signed, CSRF-protected *manual* review:
the browser supplies bounded numbers, the server returns the score breakdown
and recommendation, and nothing is stored or sent to another authority.

It deliberately does not import the Bot or bridge, connect to a platform,
call an AI/provider, create a job, change a wallet/ledger, start PayOS,
publish content, create an asset or claim that revenue is canonical.
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator

from copyfast_auth import envelope, require_account, require_csrf
from copyfast_db import growth_review_enabled


router = APIRouter(prefix="/api/v1/growth-review", tags=["Web Growth Review"])

PLATFORMS = frozenset({"facebook", "instagram", "tiktok", "youtube", "threads", "website", "other"})
PLATFORM_LABELS = {
    "facebook": "Facebook",
    "instagram": "Instagram",
    "tiktok": "TikTok",
    "youtube": "YouTube",
    "threads": "Threads",
    "website": "Website",
    "other": "Nền tảng khác",
}
SCORE_VERSION = "bot-growth-rules-v1"
MAX_EVENT_COUNT = 2_000_000_000
MAX_MANUAL_ATTRIBUTED_VALUE_VND = 9_000_000_000_000
UNSAFE_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
MARKUP_OR_EXECUTION_PATTERN = re.compile(
    r"(?:<\s*/?\s*[A-Za-z][^>\r\n]{0,240}>|\[[^\]\r\n]{1,160}\]\([^\)\r\n]{1,480}\)|```|\bon[a-z]+\s*=)",
    re.IGNORECASE,
)
URL_OR_PATH_PATTERN = re.compile(
    r"(?:\b(?:https?|ftp)://|\bwww\.|\b(?:file|data|javascript|blob):|(?:^|\s)[A-Za-z]:[\\/]|(?:^|\s)/(?:[A-Za-z0-9_.-]+/){1,})",
    re.IGNORECASE,
)
SECRET_PATTERN = re.compile(
    r"\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|client[ _-]?secret|"
    r"password|passphrase|authorization|otp|cvv|cvc|private[ _-]?key)\b\s*(?:['\"]\s*)?(?:[:=]|\bis\b)\s*(?:['\"]\s*)?[A-Za-z0-9_./+=:-]{6,}",
    re.IGNORECASE,
)
KNOWN_SECRET_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(?:sk|pk|rk)_[A-Za-z0-9_-]{12}|github_pat_[A-Za-z0-9_]{12}|"
    r"gh[pousr]_[A-Za-z0-9]{12}|xox[bpars]-[A-Za-z0-9-]{12}|AIza[0-9A-Za-z_-]{20}|"
    r"(?:AKIA|ASIA)[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}\.",
    re.IGNORECASE,
)


def _require_enabled() -> None:
    if not growth_review_enabled():
        raise HTTPException(
            status_code=503,
            detail="Growth Review đang tạm dừng để bảo trì. WEBAPP_GROWTH_REVIEW_ENABLED chưa được bật.",
        )


def _boundary(**extra: Any) -> dict[str, Any]:
    """Return a complete, explicit non-authority boundary for Portal checks."""

    value: dict[str, Any] = {
        "execution": "web_native_manual_rule_review_only",
        "input_persisted": False,
        "manual_metrics_only": True,
        "platform_connected": False,
        "platform_data_verified": False,
        "canonical_revenue_read": False,
        "canonical_revenue_written": False,
        "ai_model_called": False,
        "provider_called": False,
        "bot_called": False,
        "bridge_called": False,
        "job_created": False,
        "wallet_mutated": False,
        "payment_started": False,
        "asset_saved": False,
        "publish_action_created": False,
        "delivery_created": False,
    }
    value.update(extra)
    return value


def _content_label(value: str) -> str:
    if "\r" in value or "\n" in value:
        raise ValueError("Nhãn nội dung phải nằm trên một dòng")
    label = re.sub(r"\s+", " ", value).strip()
    if UNSAFE_CONTROL_PATTERN.search(label) or not 2 <= len(label) <= 160:
        raise ValueError("Nhãn nội dung cần từ 2 đến 160 ký tự hợp lệ")
    if MARKUP_OR_EXECUTION_PATTERN.search(label) or URL_OR_PATH_PATTERN.search(label):
        raise ValueError("Nhãn nội dung không nhận markup, URL hoặc đường dẫn")
    if SECRET_PATTERN.search(label) or KNOWN_SECRET_PATTERN.search(label):
        raise ValueError("Nhãn nội dung không nhận secret, token hoặc thông tin xác thực")
    return label


def _platform(value: str) -> str:
    platform = str(value).strip().lower()
    if platform not in PLATFORMS:
        raise ValueError("Nền tảng Growth Review không hợp lệ")
    return platform


class GrowthReviewRequest(BaseModel):
    """The closed, manual metric schema accepted by the rule evaluator.

    Numbers must be browser-entered integer observations.  In particular,
    ``manual_attributed_value_vnd`` is not a transaction, invoice, wallet
    balance or canonical revenue value; it merely preserves the compatible
    decision threshold from the Bot helper without asserting financial truth.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    content_label: StrictStr
    platform: StrictStr
    views: StrictInt = Field(ge=0, le=MAX_EVENT_COUNT)
    likes: StrictInt = Field(ge=0, le=MAX_EVENT_COUNT)
    comments: StrictInt = Field(ge=0, le=MAX_EVENT_COUNT)
    shares: StrictInt = Field(ge=0, le=MAX_EVENT_COUNT)
    clicks: StrictInt = Field(ge=0, le=MAX_EVENT_COUNT)
    manual_attributed_value_vnd: StrictInt = Field(default=0, ge=0, le=MAX_MANUAL_ATTRIBUTED_VALUE_VND)

    @field_validator("content_label")
    @classmethod
    def validate_content_label(cls, value: str) -> str:
        return _content_label(value)

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, value: str) -> str:
        return _platform(value)


def calculate_performance_score(
    *,
    views: int,
    likes: int,
    comments: int,
    shares: int,
    clicks: int,
    manual_attributed_value_vnd: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Mirror the Bot helper's threshold math without importing Bot code.

    The breakdown makes each deterministic point allocation inspectable.  It
    is a local decision aid, not a platform score or model prediction.
    """

    engagement = likes + comments + shares
    view_points = 30 if views >= 10_000 else 25 if views >= 5_000 else 15 if views >= 1_000 else 8 if views >= 300 else 0
    engagement_points = 20 if engagement > 100 else 10 if engagement > 30 else 0
    click_points = 20 if clicks > 50 else 10 if clicks > 10 else 5 if clicks > 0 else 0
    value_points = 35 if manual_attributed_value_vnd > 100_000 else 25 if manual_attributed_value_vnd > 0 else 0
    total = min(100, view_points + engagement_points + click_points + value_points)
    return total, [
        {"key": "views", "label": "Lượt xem tự nhập", "observed": views, "points": view_points, "max_points": 30},
        {"key": "engagement", "label": "Tương tác tự nhập", "observed": engagement, "points": engagement_points, "max_points": 20},
        {"key": "clicks", "label": "Click tự nhập", "observed": clicks, "points": click_points, "max_points": 20},
        {"key": "manual_attributed_value_vnd", "label": "Giá trị quy đổi tự nhập (VND)", "observed": manual_attributed_value_vnd, "points": value_points, "max_points": 35},
    ]


def build_growth_recommendation(payload: GrowthReviewRequest) -> dict[str, str | int]:
    """Mirror the Bot helper's explicit priority ordering, transparently."""

    score, _ = calculate_performance_score(
        views=payload.views,
        likes=payload.likes,
        comments=payload.comments,
        shares=payload.shares,
        clicks=payload.clicks,
        manual_attributed_value_vnd=payload.manual_attributed_value_vnd,
    )
    engagement = payload.likes + payload.comments + payload.shares
    platform = PLATFORM_LABELS[payload.platform]
    if payload.manual_attributed_value_vnd > 0 and payload.clicks > 0:
        return {
            "type": "scale",
            "title": "Mở rộng biến thể đang có tín hiệu",
            "reason": "Bạn đã tự ghi nhận click và giá trị quy đổi. Điều này là tín hiệu để kiểm tra thêm, không phải xác nhận doanh thu canonical.",
            "action": f"Tạo ba biến thể cùng angle, giữ CTA hiện tại và tự kiểm tra lại khả năng phù hợp trên {platform} trước khi đăng.",
            "score": score,
        }
    if payload.views >= 1_000 and payload.clicks <= 3:
        return {
            "type": "fix_cta",
            "title": "Rà soát CTA trước khi tăng phân phối",
            "reason": "Lượt xem tự nhập đã cao hơn ngưỡng nhưng click tự nhập còn thấp. Có thể cần làm rõ caption, comment ghim hoặc lời kêu gọi hành động.",
            "action": "Giữ hook, viết lại CTA, thêm disclosure phù hợp nếu có affiliate và tự kiểm tra lại link/offer trước khi đăng.",
            "score": score,
        }
    if payload.views < 300:
        return {
            "type": "fix_hook",
            "title": "Viết lại hook và khung mở đầu",
            "reason": "Lượt xem tự nhập còn thấp; phần mở đầu có thể chưa tạo đủ lý do để người xem dừng lại.",
            "action": "Soạn ba hook mới, đổi text/thumbnail mở đầu và thử một angle nguyên bản khác trước lần đăng tiếp theo.",
            "score": score,
        }
    if engagement >= 30 and payload.manual_attributed_value_vnd <= 0:
        return {
            "type": "add_offer",
            "title": "Làm rõ offer và vị trí chuyển đổi",
            "reason": "Có tương tác tự nhập nhưng chưa có giá trị quy đổi tự nhập. Hãy tự kiểm tra sản phẩm, lợi ích và vị trí CTA trước khi kết luận.",
            "action": "Làm rõ offer/link trong caption hoặc comment ghim, rồi tạo phiên bản review trực diện hơn để tự kiểm chứng.",
            "score": score,
        }
    return {
        "type": "pause_or_rewrite",
        "title": "Tạm dừng mở rộng và viết lại có chủ đích",
        "reason": "Các chỉ số tự nhập hiện chưa đủ mạnh để mở rộng một cách có trách nhiệm.",
        "action": "Đổi topic, hook, platform hoặc góc triển khai; chỉ đánh giá lại sau khi bạn có một quan sát mới tự kiểm tra.",
        "score": score,
    }


def _score_band(score: int) -> dict[str, str]:
    if score >= 75:
        return {"key": "strong", "label": "Tín hiệu mạnh để tự kiểm chứng thêm"}
    if score >= 45:
        return {"key": "promising", "label": "Có tín hiệu, cần tối ưu có chủ đích"}
    if score >= 20:
        return {"key": "early", "label": "Tín hiệu sớm, ưu tiên thử nghiệm nhỏ"}
    return {"key": "weak", "label": "Chưa đủ tín hiệu để mở rộng"}


def _review(payload: GrowthReviewRequest) -> dict[str, Any]:
    score, breakdown = calculate_performance_score(
        views=payload.views,
        likes=payload.likes,
        comments=payload.comments,
        shares=payload.shares,
        clicks=payload.clicks,
        manual_attributed_value_vnd=payload.manual_attributed_value_vnd,
    )
    recommendation = build_growth_recommendation(payload)
    return {
        "content_label": payload.content_label,
        "platform": payload.platform,
        "platform_label": PLATFORM_LABELS[payload.platform],
        "manual_inputs": {
            "views": payload.views,
            "likes": payload.likes,
            "comments": payload.comments,
            "shares": payload.shares,
            "clicks": payload.clicks,
            "manual_attributed_value_vnd": payload.manual_attributed_value_vnd,
        },
        "engagement_total": payload.likes + payload.comments + payload.shares,
        "score": score,
        "score_band": _score_band(score),
        "score_breakdown": breakdown,
        "recommendation": recommendation,
        "rule_version": SCORE_VERSION,
        "provenance": {
            "kind": "manual_account_input",
            "platform_data_verified": False,
            "canonical_revenue": False,
            "input_persisted": False,
            "evaluated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        },
        "next_workflows": [
            {"label": "Content Prompt Pack", "route": "/content/prompt-pack", "purpose": "Soạn biến thể content để tự review."},
            {"label": "Gói review trước khi đăng", "route": "/content/publish-review", "purpose": "Rà title, caption, hashtag và CTA trước khi tự đăng."},
            {"label": "Analytics Workspace", "route": "/analytics", "purpose": "Lưu quan sát thủ công có lịch sử riêng nếu cần."},
        ],
    }


@router.get("/policy")
async def growth_review_policy(account: dict = Depends(require_account)):
    """Expose a signed, read-only capability statement for the Portal."""

    del account
    _require_enabled()
    return envelope(
        True,
        "Growth Review dùng công thức xác định trên số liệu bạn tự nhập; không phải Growth AI, không đọc dữ liệu nền tảng hoặc doanh thu canonical.",
        data={
            "rule_version": SCORE_VERSION,
            "platforms": [{"key": key, "label": PLATFORM_LABELS[key]} for key in sorted(PLATFORMS)],
            "limits": {"max_event_count": MAX_EVENT_COUNT, "max_manual_attributed_value_vnd": MAX_MANUAL_ATTRIBUTED_VALUE_VND},
            **_boundary(),
        },
        status_name="read_only",
    )


@router.post("/evaluate")
async def evaluate_growth_review(payload: GrowthReviewRequest, account: dict = Depends(require_csrf)):
    """Evaluate one manual metric set without persisting or dispatching it."""

    _require_enabled()
    del account
    review = _review(payload)
    return envelope(
        True,
        "Đã tạo Growth Review rule-based từ số liệu bạn tự nhập. Kết quả không được lưu, không xác minh dữ liệu nền tảng và không tạo hành động bên ngoài.",
        data={"review": review, **_boundary()},
        status_name="draft",
    )
