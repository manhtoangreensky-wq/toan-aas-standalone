"""Signed, deterministic Quick Image Planner for the standalone Web App.

The frozen Telegram Bot's Quick Image conversation is useful before it reaches
its canonical tier/credit/ShopAI confirmation branch: choose a seed or write a
brief, refine a prompt and select an aspect ratio.  This module ports only that
planning grammar into an independent Web workspace.  It intentionally creates
no image, preview, Asset Vault record, Bot pending state, provider request,
job, Xu/wallet mutation, PayOS payment, publish action or delivery.

The Bot remains the authority for its own account state and any later
generation/charge flow.  A browser never receives Telegram callback values,
confirm tokens, tier prices, provider identifiers or an execution handle.
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr, field_validator, model_validator

from copyfast_auth import envelope, require_csrf
from copyfast_db import quick_image_planner_enabled
from copyfast_trend_research import (
    LANGUAGES,
    MARKUP_PATTERN,
    POLICY_GUARD_PATTERNS,
    SOCIAL_HANDLE_PATTERN,
    UNSAFE_CONTROL_PATTERN,
    URL_OR_PATH_PATTERN,
    _sensitive,
)


router = APIRouter(prefix="/api/v1/quick-image-planner", tags=["Web Quick Image Planner"])

IDEA_SOURCES = frozenset({"curated", "custom"})
ASPECT_RATIOS = frozenset({"1:1", "4:5", "9:16", "16:9", "3:4", "3:2", "4:3"})
VARIATIONS = frozenset({0, 1, 2})
BRAND_POSITIONS = frozenset({
    "none", "top_left", "top_center", "top_right", "center_left", "center", "center_right",
    "bottom_left", "bottom_center", "bottom_right",
})

# These are Web-owned, finite catalog keys.  They deliberately do not mirror
# the Bot's callback payloads and contain no URL, provider, asset or job data.
CURATED_IDEAS: dict[str, dict[str, str]] = {
    "desk_organizer": {
        "vi": "Góc bàn làm việc gọn gàng với một giải pháp tổ chức tối giản",
        "en": "A tidy desk setup with one minimal organisation solution",
    },
    "daily_bottle": {
        "vi": "Bình nước giữ nhiệt trong nhịp sống năng động hằng ngày",
        "en": "An insulated bottle in an active everyday routine",
    },
    "small_shop": {
        "vi": "Sản phẩm thủ công của cửa hàng nhỏ trong bối cảnh gần gũi",
        "en": "A small shop's handmade product in a warm everyday setting",
    },
    "skincare_ritual": {
        "vi": "Nghi thức chăm sóc da nhẹ nhàng với sản phẩm chủ đạo rõ ràng",
        "en": "A calm skincare ritual with one clear hero product",
    },
    "coffee_moment": {
        "vi": "Khoảnh khắc cà phê sáng tại nhà với ánh sáng tự nhiên",
        "en": "A morning coffee moment at home with natural light",
    },
    "travel_essential": {
        "vi": "Một vật dụng du lịch thiết yếu được sử dụng đúng ngữ cảnh",
        "en": "A travel essential used in a realistic context",
    },
    "learning_tool": {
        "vi": "Công cụ học tập giúp một thao tác thường ngày rõ ràng hơn",
        "en": "A learning tool making one everyday step clearer",
    },
    "home_comfort": {
        "vi": "Chi tiết trang trí nhà tạo cảm giác ấm áp và dễ sống",
        "en": "A home detail that makes a space feel warm and lived in",
    },
    "local_food": {
        "vi": "Món ăn địa phương được bày biện tự nhiên, sạch và chân thực",
        "en": "A local dish presented naturally, cleanly and authentically",
    },
    "quiet_reading": {
        "vi": "Khoảnh khắc đọc sách yên tĩnh với ánh sáng chiều dịu",
        "en": "A quiet reading moment in soft afternoon light",
    },
    "eco_routine": {
        "vi": "Một thói quen sống xanh nhỏ nhưng thực tế trong căn bếp",
        "en": "A small, practical eco-conscious routine in the kitchen",
    },
    "pet_care": {
        "vi": "Chăm sóc thú cưng trong không gian nhà sáng sủa và tự nhiên",
        "en": "Pet care in a bright, natural home setting",
    },
    "fitness_reset": {
        "vi": "Góc chuẩn bị tập luyện nhẹ nhàng cho một ngày bận rộn",
        "en": "A gentle workout setup for a busy day",
    },
    "weekend_market": {
        "vi": "Một quầy hàng cuối tuần nhỏ với sản phẩm địa phương chân thực",
        "en": "A small weekend market stall with authentic local products",
    },
    "creative_stationery": {
        "vi": "Dụng cụ văn phòng phẩm sáng tạo trên nền bàn làm việc sạch",
        "en": "Creative stationery on a clean working desk",
    },
    "family_meal": {
        "vi": "Bữa ăn gia đình ấm cúng với một chi tiết sản phẩm tinh tế",
        "en": "A warm family meal with one subtle product detail",
    },
    "morning_cycle": {
        "vi": "Chuẩn bị cho chuyến đạp xe buổi sáng với dụng cụ thiết yếu",
        "en": "Preparing for a morning cycle with an essential item",
    },
    "plant_corner": {
        "vi": "Góc cây xanh trong căn hộ nhỏ với cảm giác thư giãn",
        "en": "A relaxing plant corner in a small apartment",
    },
    "craft_process": {
        "vi": "Quy trình làm thủ công có bàn tay người thật và vật liệu rõ ràng",
        "en": "A handmade process with real hands and clear materials",
    },
    "remote_meeting": {
        "vi": "Không gian họp từ xa gọn gàng, chuyên nghiệp và gần gũi",
        "en": "A tidy, professional and approachable remote meeting space",
    },
    "gift_wrap": {
        "vi": "Gói quà tối giản với chất liệu giấy và ruy băng tự nhiên",
        "en": "Minimal gift wrapping with natural paper and ribbon",
    },
    "night_skincare": {
        "vi": "Chuẩn bị chăm sóc da buổi tối với ánh sáng ấm và dịu",
        "en": "An evening skincare setup in warm, gentle light",
    },
    "makers_table": {
        "vi": "Bàn làm việc của người sáng tạo với công cụ và ý tưởng đang mở",
        "en": "A maker's table with tools and an idea in progress",
    },
    "community_class": {
        "vi": "Buổi học cộng đồng nhỏ với không khí tích cực và chân thực",
        "en": "A small community class with a positive, authentic atmosphere",
    },
}


def _require_enabled() -> None:
    if not quick_image_planner_enabled():
        raise HTTPException(
            status_code=503,
            detail=(
                "Quick Image Planner đang tạm dừng để bảo trì. "
                "WEBAPP_QUICK_IMAGE_PLANNER_ENABLED chưa được bật."
            ),
        )


def _safe_line(value: str, *, field: str, minimum: int, maximum: int, allow_empty: bool = False) -> str:
    """Normalize one bounded text field without accepting a transport handle."""

    if "\r" in value or "\n" in value:
        raise ValueError(f"{field} phải nằm trên một dòng")
    normalized = re.sub(r"\s+", " ", value).strip()
    if allow_empty and not normalized:
        return ""
    if UNSAFE_CONTROL_PATTERN.search(normalized) or not minimum <= len(normalized) <= maximum:
        raise ValueError(f"{field} cần từ {minimum} đến {maximum} ký tự hợp lệ")
    if MARKUP_PATTERN.search(normalized) or URL_OR_PATH_PATTERN.search(normalized) or SOCIAL_HANDLE_PATTERN.search(normalized):
        raise ValueError(f"{field} không nhận markup, URL, path, tệp hoặc social handle")
    if _sensitive(normalized):
        raise ValueError(f"{field} không nhận secret, token, OTP hoặc dữ liệu thẻ")
    return normalized


class QuickImagePlannerRequest(BaseModel):
    """Exact request for one transient, no-execution image prompt plan.

    ``suggestion_key`` is a closed Web-owned catalog key, never a Bot callback
    or dynamic topic. Custom text, ratio, optional brand direction and a
    finite rewrite variation are the only browser inputs.  There is purposely
    no source image/URL/path, provider/model/tier, confirm token, project,
    asset, job, payment, wallet, idempotency or publish field.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    idea_source: StrictStr
    suggestion_key: StrictStr = ""
    custom_prompt: StrictStr = ""
    aspect_ratio: StrictStr = "1:1"
    variation: StrictInt = 0
    brand_direction: StrictStr = ""
    brand_position: StrictStr = "none"
    language: StrictStr = "vi"

    @field_validator("idea_source")
    @classmethod
    def validate_idea_source(cls, value: str) -> str:
        source = str(value).strip().lower()
        if source not in IDEA_SOURCES:
            raise ValueError("Nguồn ý tưởng chỉ hỗ trợ curated hoặc custom")
        return source

    @field_validator("suggestion_key")
    @classmethod
    def validate_suggestion_key(cls, value: str) -> str:
        key = str(value).strip().lower()
        if key and key not in CURATED_IDEAS:
            raise ValueError("Gợi ý ảnh không hợp lệ")
        return key

    @field_validator("custom_prompt")
    @classmethod
    def validate_custom_prompt(cls, value: str) -> str:
        return _safe_line(value, field="Mô tả riêng", minimum=4, maximum=1400, allow_empty=True)

    @field_validator("aspect_ratio")
    @classmethod
    def validate_aspect_ratio(cls, value: str) -> str:
        ratio = str(value).strip()
        if ratio not in ASPECT_RATIOS:
            raise ValueError("Tỷ lệ ảnh không hợp lệ")
        return ratio

    @field_validator("variation")
    @classmethod
    def validate_variation(cls, value: int) -> int:
        if value not in VARIATIONS:
            raise ValueError("Biến thể prompt không hợp lệ")
        return value

    @field_validator("brand_direction")
    @classmethod
    def validate_brand_direction(cls, value: str) -> str:
        # The frozen Bot accepts up to 300 characters of text watermark input.
        # Keep that user-visible limit while treating it only as a direction
        # for a later human-approved runtime, never as an overlay operation.
        return _safe_line(value, field="Hướng thương hiệu", minimum=2, maximum=300, allow_empty=True)

    @field_validator("brand_position")
    @classmethod
    def validate_brand_position(cls, value: str) -> str:
        position = str(value).strip().lower()
        if position not in BRAND_POSITIONS:
            raise ValueError("Vị trí logo/watermark không hợp lệ")
        return position

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        language = str(value).strip().lower()
        if language not in LANGUAGES:
            raise ValueError("Ngôn ngữ Quick Image Planner chỉ hỗ trợ vi hoặc en")
        return language

    @model_validator(mode="after")
    def validate_source_contract(self) -> "QuickImagePlannerRequest":
        if self.idea_source == "curated":
            if not self.suggestion_key:
                raise ValueError("Hãy chọn một gợi ý ảnh")
            if self.custom_prompt:
                raise ValueError("Gợi ý có sẵn không nhận mô tả riêng đồng thời")
        else:
            if self.suggestion_key:
                raise ValueError("Mô tả riêng không nhận mã gợi ý")
            if not self.custom_prompt:
                raise ValueError("Hãy nhập mô tả ảnh riêng")
        if not self.brand_direction and self.brand_position != "none":
            raise ValueError("Cần nhập hướng thương hiệu trước khi chọn vị trí logo/watermark")
        if self.brand_direction and self.brand_position == "none":
            raise ValueError("Hãy chọn vị trí logo/watermark hoặc bỏ hướng thương hiệu")
        return self


def _boundary() -> dict[str, Any]:
    """Complete browser-verifiable boundary for a text planning receipt."""

    return {
        "execution": "web_native_deterministic_quick_image_planner_only",
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


def _topic(payload: QuickImagePlannerRequest) -> str:
    if payload.idea_source == "custom":
        return payload.custom_prompt
    return CURATED_IDEAS[payload.suggestion_key][payload.language]


def _policy_guard(payload: QuickImagePlannerRequest) -> dict[str, Any] | None:
    text = " ".join(value for value in (_topic(payload), payload.brand_direction) if value)
    if not any(pattern.search(text) for pattern in POLICY_GUARD_PATTERNS):
        return None
    return envelope(
        False,
        (
            "Ý tưởng cần được viết lại theo hướng sáng tạo nguyên bản. Quick Image Planner "
            "không hỗ trợ reup/copy không có quyền, né watermark/DRM/Content ID, mạo danh, "
            "clone hoặc deepfake người thật."
        ),
        data=_boundary(),
        status_name="guarded",
        error_code="WEB_QUICK_IMAGE_PLANNER_POLICY_GUARD",
    )


def _variation_copy(variation: int, language: str) -> tuple[str, str, str]:
    if language == "en":
        variants = (
            ("Clean product direction", "clean commercial product photography", "clear subject, practical detail, no exaggerated result"),
            ("Everyday lifestyle direction", "authentic lifestyle photography", "human-scale context, lived-in detail, natural moment"),
            ("Editorial story direction", "calm editorial visual storytelling", "considered composition, genuine texture, understated narrative"),
        )
    else:
        variants = (
            ("Hướng sản phẩm sạch", "clean commercial product photography", "chủ thể rõ, chi tiết thực tế, không phóng đại kết quả"),
            ("Hướng lifestyle đời thường", "authentic lifestyle photography", "bối cảnh gần gũi, chi tiết có người dùng, khoảnh khắc tự nhiên"),
            ("Hướng editorial kể chuyện", "calm editorial visual storytelling", "bố cục có chủ đích, chất liệu chân thực, câu chuyện nhẹ"),
        )
    return variants[variation]


def _brand_position_label(position: str, language: str) -> str:
    labels = {
        "top_left": ("top left", "trên trái"),
        "top_center": ("top centre", "trên giữa"),
        "top_right": ("top right", "trên phải"),
        "center_left": ("centre left", "giữa trái"),
        "center": ("centre", "chính giữa"),
        "center_right": ("centre right", "giữa phải"),
        "bottom_left": ("bottom left", "dưới trái"),
        "bottom_center": ("bottom centre", "dưới giữa"),
        "bottom_right": ("bottom right", "dưới phải"),
        "none": ("not requested", "không yêu cầu"),
    }
    return labels[position][0 if language == "en" else 1]


def _compose_plan(payload: QuickImagePlannerRequest) -> dict[str, Any]:
    topic = _topic(payload)
    title, visual_style, composition = _variation_copy(payload.variation, payload.language)
    brand = payload.brand_direction
    position = _brand_position_label(payload.brand_position, payload.language)
    brand_clause = (
        f" Brand direction: {brand}; reserve the {position} area for manual review only." if brand and payload.language == "en"
        else f" Hướng thương hiệu: {brand}; chừa vùng {position} để người duyệt xử lý thủ công." if brand
        else " Keep brand text and logos absent unless you have verified rights." if payload.language == "en"
        else " Không thêm text hoặc logo nếu chưa tự xác nhận quyền sử dụng."
    )
    if payload.language == "en":
        short_prompt = f"{topic}, {visual_style}, {composition}, {payload.aspect_ratio} aspect ratio."
        detailed_prompt = (
            f"Create an original image about {topic}. Use {visual_style}; {composition}. "
            f"Frame for a {payload.aspect_ratio} aspect ratio, soft natural light, realistic materials, "
            "balanced colour, one readable focal point and respectful human context where relevant."
            f"{brand_clause}"
        )
        negative_prompt = (
            "watermark, copied creator style, unlicensed logo, fake text, distorted hands, deformed product, "
            "misleading before-and-after, celebrity likeness, deepfake, oversharpening, clutter"
        )
        review_checklist = [
            "Confirm you own or have permission for every reference, person, logo, brand and claim before real use.",
            "Check product details, pricing, performance and before/after language manually; this planner verifies none of them.",
            "Review any generated text or logo separately; do not treat this prompt plan as an approved visual output.",
            "Choose a separately approved runtime only after a human review and its own estimate/confirmation flow.",
        ]
        unavailable = [
            "No image, preview, upload, source-image analysis or Asset Vault record is created.",
            "No model/provider, Bot/Core Bridge, ShopAI, external URL or live source is called.",
            "No tier price, Xu/wallet mutation, PayOS payment, job, confirmation token or delivery is created.",
            "The Bot's tier and confirm-generation branch remains canonical and is not invoked from this planner.",
        ]
        next_workflows = [
            {"label": "Image Prompt Composer", "route": "/image/prompt-composer", "purpose": "Expand this direction into a separate structured prompt draft."},
            {"label": "Image Creative Studio", "route": "/image-studio", "purpose": "Create a Web-owned art direction with version history when you deliberately choose to save one."},
            {"label": "Content Prompt Pack", "route": "/content/prompt-pack", "purpose": "Prepare the related hook, caption and content text for human review."},
        ]
        title_text = f"Quick Image Plan: {topic[:180]}"
        summary = "Prompt plan only — no image generation runtime is connected."
    else:
        short_prompt = f"{topic}, {visual_style}, {composition}, tỷ lệ {payload.aspect_ratio}."
        detailed_prompt = (
            f"Tạo một hình ảnh nguyên bản về {topic}. Dùng phong cách {visual_style}; {composition}. "
            f"Bố cục theo tỷ lệ {payload.aspect_ratio}, ánh sáng tự nhiên mềm, chất liệu chân thực, màu cân bằng, "
            "một điểm nhìn rõ và bối cảnh tôn trọng con người khi phù hợp."
            f"{brand_clause}"
        )
        negative_prompt = (
            "watermark, copied creator style, unlicensed logo, fake text, distorted hands, deformed product, "
            "misleading before-and-after, celebrity likeness, deepfake, oversharpening, clutter"
        )
        review_checklist = [
            "Xác nhận bạn có quyền dùng mọi reference, người, logo, thương hiệu và claim trước khi dùng thật.",
            "Tự kiểm tra chi tiết sản phẩm, giá, hiệu năng và diễn đạt before/after; planner không xác minh các nội dung này.",
            "Rà soát riêng text hoặc logo sinh ra; không coi prompt plan là ảnh đã được duyệt hoặc output thật.",
            "Chỉ chọn runtime được cấp riêng sau human review và flow estimate/xác nhận của chính runtime đó.",
        ]
        unavailable = [
            "Không tạo ảnh, preview, upload, phân tích ảnh nguồn hoặc Asset Vault record.",
            "Không gọi model/provider, Bot/Core Bridge, ShopAI, URL bên ngoài hoặc nguồn live.",
            "Không tạo giá tier, thay đổi ví Xu, PayOS payment, job, confirm token hoặc delivery.",
            "Nhánh chọn tier/xác nhận tạo của Bot vẫn là canonical và không được gọi từ planner này.",
        ]
        next_workflows = [
            {"label": "Image Prompt Composer", "route": "/image/prompt-composer", "purpose": "Mở rộng direction này thành prompt có cấu trúc ở một workspace riêng."},
            {"label": "Image Creative Studio", "route": "/image-studio", "purpose": "Tạo art direction Web-owned có version history khi bạn chủ động muốn lưu."},
            {"label": "Content Prompt Pack", "route": "/content/prompt-pack", "purpose": "Chuẩn bị hook, caption và nội dung liên quan để người duyệt kiểm tra."},
        ]
        title_text = f"Kế hoạch ảnh nhanh: {topic[:180]}"
        summary = "Chỉ có prompt plan — chưa kết nối runtime tạo ảnh."

    return {
        "title": title_text,
        "language": payload.language,
        "idea_source": payload.idea_source,
        "suggestion_key": payload.suggestion_key if payload.idea_source == "curated" else "",
        "topic": topic,
        "variation": payload.variation,
        "variation_label": title,
        "aspect_ratio": payload.aspect_ratio,
        "brand_direction": brand,
        "brand_position": payload.brand_position,
        "brand_position_label": position,
        "short_prompt": short_prompt,
        "detailed_prompt": detailed_prompt,
        "negative_prompt": negative_prompt,
        "composition": composition,
        "output_status": "prompt_plan_only_no_real_image",
        "summary": summary,
        "review_checklist": review_checklist,
        "unavailable_capabilities": unavailable,
        "next_workflows": next_workflows,
    }


@router.post("/plan")
async def create_quick_image_plan(
    payload: QuickImagePlannerRequest,
    account: dict = Depends(require_csrf),
):
    """Return a transient plan without recording or executing an image request."""

    _require_enabled()
    del account
    guarded = _policy_guard(payload)
    if guarded:
        return guarded
    return envelope(
        True,
        (
            "Đã tạo Quick Image Plan để bạn review. Không có ảnh, preview, provider, Bot, "
            "ShopAI, job, Xu, PayOS hoặc delivery nào được tạo."
        ),
        data={"plan": _compose_plan(payload), **_boundary()},
        status_name="draft",
    )
