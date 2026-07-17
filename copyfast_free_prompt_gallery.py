"""Signed-session, read-only Free Prompt Gallery for the standalone Web App.

The frozen Telegram Free Tools Hub is only a reviewed design reference.  This
module deliberately carries a compact, immutable snapshot of its global
prompt seeds instead of importing the Bot, opening a Bot data file, sharing a
database table, or relying on a Telegram conversation.  Every request is a
deterministic read of that snapshot.  It never persists gallery input, calls a
provider or bridge, creates a job, changes a wallet, starts payment, stores an
asset, publishes content, or delivers media.

``router`` is mounted by the standalone application's composition root.  The
module stays independently mountable so its signed-session boundary can also
be exercised in focused tests without starting the whole application.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse

from copyfast_auth import envelope, require_account


router = APIRouter(prefix="/api/v1/free-prompt-gallery", tags=["Web Free Prompt Gallery"])

SNAPSHOT_VERSION = "2026-07-15.1"
SNAPSHOT_DESCRIPTION = "Bộ seed prompt Free Hub đã rà soát, cố định cho Web App."
MAX_QUERY_LENGTH = 160
MAX_PAGE_SIZE = 50
MAX_PAGE = 10_000
IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,79}$")
ITEM_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,180}$")
UNSAFE_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SECRET_QUERY_PATTERN = re.compile(
    r"\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|"
    r"client[ _-]?secret|password|passphrase|authorization|bearer)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PromptIndustry:
    """A reviewed, non-user-specific industry substitution record."""

    id: str
    title: str
    product: str
    audience: str
    benefit: str


@dataclass(frozen=True)
class PromptCategory:
    """One reviewed template family from the Free Hub snapshot."""

    id: str
    title: str
    goals: tuple[str, ...]
    platforms: tuple[str, ...]
    title_template: str
    prompt_template: str


# Static, reviewed Web snapshot.  These values intentionally live in this
# module: production Web must not open or import any Bot file/path at runtime.
INDUSTRIES: tuple[PromptIndustry, ...] = (
    PromptIndustry("shop_online", "Shop online", "sản phẩm bán online", "khách mua hàng 18-35", "mua nhanh và hiểu rõ lợi ích"),
    PromptIndustry("affiliate", "Affiliate", "sản phẩm affiliate", "người mới cần review chân thật", "chọn đúng sản phẩm phù hợp"),
    PromptIndustry("cosmetics", "Mỹ phẩm", "sản phẩm chăm sóc da", "người quan tâm làm đẹp", "quy trình chăm sóc dễ áp dụng"),
    PromptIndustry("fragrance", "Nước hoa", "nước hoa phong cách cá nhân", "nam nữ 18-35", "tạo dấu ấn và sự tự tin"),
    PromptIndustry("spa", "Spa / thẩm mỹ", "dịch vụ spa", "khách địa phương quan tâm ngoại hình", "trải nghiệm thư giãn và chỉn chu"),
    PromptIndustry("fashion", "Thời trang", "sản phẩm thời trang", "người mua online quan tâm phong cách", "phối đồ dễ và tự tin hơn"),
    PromptIndustry("food_cafe", "Đồ ăn / quán cafe", "món ăn hoặc đồ uống nổi bật", "người trẻ thích trải nghiệm địa điểm mới", "trải nghiệm ngon và đáng nhớ"),
    PromptIndustry("real_estate", "Bất động sản", "căn hộ hoặc không gian sống", "người đang tìm nơi ở hoặc đầu tư", "không gian phù hợp nhu cầu"),
    PromptIndustry("interior", "Nội thất", "sản phẩm nội thất", "gia đình muốn tối ưu không gian", "không gian đẹp và tiện dụng"),
    PromptIndustry("travel", "Du lịch", "trải nghiệm du lịch", "người thích khám phá", "hành trình dễ lên kế hoạch"),
    PromptIndustry("course", "Khóa học", "khóa học kỹ năng", "người mới muốn học thực tế", "học nhanh và áp dụng được"),
    PromptIndustry("saas", "Phần mềm / SaaS", "phần mềm hỗ trợ công việc", "creator và shop nhỏ", "tiết kiệm thời gian vận hành"),
    PromptIndustry("local_service", "Dịch vụ local", "dịch vụ tại địa phương", "khách hàng quanh khu vực", "được hỗ trợ nhanh và thuận tiện"),
    PromptIndustry("recruitment", "Tuyển dụng", "cơ hội việc làm", "ứng viên phù hợp", "hiểu rõ công việc và môi trường"),
    PromptIndustry("event", "Sự kiện", "sự kiện cộng đồng hoặc thương hiệu", "người quan tâm chủ đề sự kiện", "tham gia đúng trải nghiệm cần thiết"),
    PromptIndustry("mother_baby", "Mẹ và bé", "sản phẩm cho mẹ và bé", "gia đình trẻ", "chăm sóc thuận tiện và an tâm hơn"),
    PromptIndustry("pets", "Thú cưng", "sản phẩm cho thú cưng", "người nuôi chó mèo", "chăm sóc thú cưng dễ dàng"),
    PromptIndustry("fitness", "Fitness", "sản phẩm hoặc dịch vụ fitness", "người muốn cải thiện sức khỏe", "duy trì thói quen tốt"),
    PromptIndustry("personal_finance_content", "Tài chính cá nhân - content", "nội dung giáo dục tài chính cơ bản", "người muốn quản lý chi tiêu", "hiểu nguyên tắc chung, không phải tư vấn đầu tư"),
    PromptIndustry("education", "Giáo dục / kỹ năng", "nội dung giáo dục kỹ năng", "người học muốn tiến bộ", "kiến thức rõ ràng và dễ thực hành"),
)

CATEGORIES: tuple[PromptCategory, ...] = (
    PromptCategory(
        "meta_ai_video", "Prompt Meta AI Video", ("sell", "lead", "engagement"), ("tiktok", "reels", "facebook"),
        "Meta AI video - {industry}",
        "Tạo video 9:16 dài 8-15 giây cho {product}, hướng tới {audience}. Mở bằng tình huống thực tế, cho thấy hành động sử dụng rõ ràng, camera close-up chuyển medium shot rồi product reveal, ánh sáng chân thật, chuyển động ổn định, không chữ sai, không watermark. Nhấn mạnh lợi ích: {benefit}. Kết thúc bằng khung sạch để ghép CTA.",
    ),
    PromptCategory(
        "image_prompt", "Prompt ảnh", ("branding", "sell"), ("social", "poster"),
        "Ảnh quảng cáo - {industry}",
        "Ảnh quảng cáo chân thật cho {product}, chủ thể rõ, bố cục có khoảng thở, ánh sáng studio mềm, vật liệu tự nhiên, màu thương hiệu tinh tế, phù hợp {audience}, nhấn mạnh {benefit}, không chữ méo, không logo giả, không watermark.",
    ),
    PromptCategory(
        "video_prompt", "Prompt video", ("engagement", "sell"), ("tiktok", "reels"),
        "Video motion - {industry}",
        "Video 9:16 cho {product}: 0-2s close-up hook; 2-7s hành động sử dụng tự nhiên; 7-12s hero shot kết quả. Camera slow push-in, pan nhẹ, ánh sáng có chiều sâu, chuyển cảnh match cut, chủ thể nhất quán, không flicker, không vật thể méo. Lợi ích chính: {benefit}.",
    ),
    PromptCategory(
        "caption_cta", "Caption / Hashtag / CTA", ("sell", "engagement"), ("facebook", "instagram", "tiktok"),
        "Caption bán hàng - {industry}",
        "Viết caption ngắn cho {product}, mở bằng vấn đề quen thuộc của {audience}, nêu lợi ích {benefit}, giọng tự nhiên không phóng đại, kết thúc CTA mềm và 5 hashtag liên quan.",
    ),
    PromptCategory(
        "hook_script", "Hook / Kịch bản", ("sell", "educate"), ("short_video",),
        "Kịch bản 15-30 giây - {industry}",
        "Tạo 3 hook 3 giây và kịch bản 15/30 giây cho {product}. Cấu trúc problem -> demo -> benefit -> proof -> CTA; đối tượng {audience}; lợi ích {benefit}; tránh claim tuyệt đối và lời hứa không kiểm chứng.",
    ),
    PromptCategory(
        "document_checklist", "Ghi chú / Tài liệu", ("organize",), ("notes",),
        "Checklist nội dung - {industry}",
        "Tạo checklist chuẩn bị nội dung tuần cho {product}: mục tiêu, chân dung {audience}, 3 chủ đề, asset cần có, lịch đăng, CTA, bước đo hiệu quả và mục ghi chú cải thiện.",
    ),
    PromptCategory(
        "music_sfx", "Gợi ý nhạc / SFX", ("mood",), ("video",),
        "Mood nhạc - {industry}",
        "Gợi ý mood nhạc và SFX cho video {product}: nhịp phù hợp {audience}, intro gọn, whoosh nhẹ khi chuyển cảnh, soft impact lúc product reveal, không lấn voice, mô tả style để tìm trong thư viện nhạc có bản quyền phù hợp.",
    ),
)


def _item(category: PromptCategory, industry: PromptIndustry, template_index: int = 1) -> Mapping[str, Any]:
    variables = {
        "industry": industry.title,
        "product": industry.product,
        "audience": industry.audience,
        "benefit": industry.benefit,
    }
    return MappingProxyType(
        {
            "id": f"{category.id}_{industry.id}_{template_index}",
            "category_id": category.id,
            "category_title": category.title,
            "industry_id": industry.id,
            "industry": industry.title,
            "title": category.title_template.format(**variables),
            "prompt": category.prompt_template.format(**variables),
            "goals": category.goals,
            "platforms": category.platforms,
        }
    )


def expand_free_prompt_snapshot() -> tuple[Mapping[str, Any], ...]:
    """Return the stable category-major, industry-minor expansion of 140 seeds."""

    return tuple(_item(category, industry) for category in CATEGORIES for industry in INDUSTRIES)


EXPANDED_ITEMS = expand_free_prompt_snapshot()
ITEMS_BY_ID: Mapping[str, Mapping[str, Any]] = MappingProxyType({str(item["id"]): item for item in EXPANDED_ITEMS})
CATEGORY_BY_ID: Mapping[str, PromptCategory] = MappingProxyType({category.id: category for category in CATEGORIES})
INDUSTRY_BY_ID: Mapping[str, PromptIndustry] = MappingProxyType({industry.id: industry for industry in INDUSTRIES})
KNOWN_GOALS = frozenset(goal for category in CATEGORIES for goal in category.goals)
KNOWN_PLATFORMS = frozenset(platform for category in CATEGORIES for platform in category.platforms)


def _private_no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Vary"] = "Cookie"


def _safe_identifier(value: str | None, *, label: str, known: Mapping[str, Any] | frozenset[str]) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    if not IDENTIFIER_PATTERN.fullmatch(normalized) or normalized not in known:
        raise HTTPException(status_code=422, detail=f"{label} không hợp lệ")
    return normalized


def _safe_query(value: str | None) -> str:
    normalized = re.sub(r"\s+", " ", str(value or "")).strip()
    if not normalized:
        return ""
    if len(normalized) > MAX_QUERY_LENGTH or UNSAFE_CONTROL_PATTERN.search(normalized):
        raise HTTPException(status_code=422, detail=f"Từ khóa tìm kiếm tối đa {MAX_QUERY_LENGTH} ký tự hợp lệ")
    if SECRET_QUERY_PATTERN.search(normalized):
        raise HTTPException(status_code=422, detail="Từ khóa tìm kiếm không nhận secret hoặc thông tin đăng nhập")
    return normalized


def _public_item(item: Mapping[str, Any]) -> dict[str, Any]:
    """Return a fresh JSON-safe object; callers cannot mutate the snapshot."""

    return {
        "id": str(item["id"]),
        "category_id": str(item["category_id"]),
        "category_title": str(item["category_title"]),
        "industry_id": str(item["industry_id"]),
        "industry": str(item["industry"]),
        "title": str(item["title"]),
        "prompt": str(item["prompt"]),
        "goals": list(item["goals"]),
        "platforms": list(item["platforms"]),
    }


def filter_free_prompt_items(
    items: Iterable[Mapping[str, Any]],
    *,
    category_id: str = "",
    industry_id: str = "",
    goal: str = "",
    platform: str = "",
    query: str = "",
) -> tuple[Mapping[str, Any], ...]:
    """Deterministically filter an already ordered prompt iterable.

    Filter values are assumed to have been passed through the safe validators
    above.  The function remains pure for future UI/controller integration.
    """

    needle = query.casefold()
    filtered: list[Mapping[str, Any]] = []
    for item in items:
        if category_id and item["category_id"] != category_id:
            continue
        if industry_id and item["industry_id"] != industry_id:
            continue
        if goal and goal not in item["goals"]:
            continue
        if platform and platform not in item["platforms"]:
            continue
        if needle:
            searchable = " ".join(
                (
                    str(item["title"]),
                    str(item["prompt"]),
                    str(item["category_title"]),
                    str(item["industry"]),
                    " ".join(str(value) for value in item["goals"]),
                    " ".join(str(value) for value in item["platforms"]),
                )
            ).casefold()
            if needle not in searchable:
                continue
        filtered.append(item)
    return tuple(filtered)


def paginate_free_prompt_items(
    items: tuple[Mapping[str, Any], ...], *, page: int, page_size: int
) -> tuple[tuple[Mapping[str, Any], ...], dict[str, int | bool]]:
    """Return a stable slice plus explicit page metadata without persistence."""

    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)
    start = (page - 1) * page_size
    page_items = items[start : start + page_size] if start < total else ()
    return page_items, {
        "page": page,
        "page_size": page_size,
        "total_items": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": page > 1 and total > 0,
    }


def free_prompt_item(prompt_id: str) -> Mapping[str, Any] | None:
    """Look up one snapshot item without reading any file or mutable store."""

    return ITEMS_BY_ID.get(prompt_id)


def _boundaries() -> dict[str, bool | str]:
    return {
        "execution": "web_native_static_prompt_gallery",
        "snapshot_read_only": True,
        "gallery_request_persisted": False,
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


def _catalog() -> dict[str, Any]:
    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "description": SNAPSHOT_DESCRIPTION,
        "total_items": len(EXPANDED_ITEMS),
        "categories": [
            {
                "id": category.id,
                "title": category.title,
                "goals": list(category.goals),
                "platforms": list(category.platforms),
                "item_count": len(INDUSTRIES),
            }
            for category in CATEGORIES
        ],
        "industries": [
            {
                "id": industry.id,
                "title": industry.title,
                "item_count": len(CATEGORIES),
            }
            for industry in INDUSTRIES
        ],
        "boundaries": _boundaries(),
    }


@router.get("/catalog")
def get_catalog(response: Response, _: dict[str, Any] = Depends(require_account)) -> dict[str, Any]:
    """Return filter metadata for an authenticated Web account only."""

    _private_no_store(response)
    return envelope(True, "Đã tải catalog Prompt Gallery chỉ đọc.", data=_catalog(), status_name="completed")


@router.get("/items")
def get_items(
    response: Response,
    category_id: str = Query("", description="ID nhóm prompt"),
    industry_id: str = Query("", description="ID ngành"),
    goal: str = Query("", description="Mục tiêu"),
    platform: str = Query("", description="Nền tảng"),
    q: str = Query("", description="Từ khóa"),
    page: int = Query(1, ge=1, le=MAX_PAGE),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    _: dict[str, Any] = Depends(require_account),
) -> dict[str, Any]:
    """List a deterministic page of safe, read-only static prompt seeds."""

    _private_no_store(response)
    safe_category = _safe_identifier(category_id, label="Category", known=CATEGORY_BY_ID)
    safe_industry = _safe_identifier(industry_id, label="Industry", known=INDUSTRY_BY_ID)
    safe_goal = _safe_identifier(goal, label="Goal", known=KNOWN_GOALS)
    safe_platform = _safe_identifier(platform, label="Platform", known=KNOWN_PLATFORMS)
    safe_query = _safe_query(q)
    filtered = filter_free_prompt_items(
        EXPANDED_ITEMS,
        category_id=safe_category,
        industry_id=safe_industry,
        goal=safe_goal,
        platform=safe_platform,
        query=safe_query,
    )
    page_items, pagination = paginate_free_prompt_items(filtered, page=page, page_size=page_size)
    return envelope(
        True,
        "Đã tải Prompt Gallery chỉ đọc.",
        data={
            "snapshot_version": SNAPSHOT_VERSION,
            "filters": {
                "category_id": safe_category,
                "industry_id": safe_industry,
                "goal": safe_goal,
                "platform": safe_platform,
                "q": safe_query,
            },
            "pagination": pagination,
            "items": [_public_item(item) for item in page_items],
            "boundaries": _boundaries(),
        },
        status_name="completed",
    )


@router.get("/items/{prompt_id}", response_model=None)
def get_item(prompt_id: str, response: Response, _: dict[str, Any] = Depends(require_account)) -> Any:
    """Return a single static prompt seed after strict ID validation."""

    _private_no_store(response)
    normalized = str(prompt_id or "").strip()
    if not ITEM_ID_PATTERN.fullmatch(normalized):
        raise HTTPException(status_code=422, detail="Prompt ID không hợp lệ")
    item = free_prompt_item(normalized)
    if item is None:
        return JSONResponse(
            envelope(False, "Không tìm thấy prompt trong snapshot hiện tại.", status_name="guarded", error_code="WEB_FREE_PROMPT_NOT_FOUND"),
            status_code=404,
            headers={"Cache-Control": "private, no-store", "Pragma": "no-cache", "Vary": "Cookie"},
        )
    return envelope(
        True,
        "Đã tải chi tiết prompt chỉ đọc.",
        data={
            "snapshot_version": SNAPSHOT_VERSION,
            "item": _public_item(item),
            "copy_instruction": "Dùng seed này làm brief hoặc prompt; tự rà soát sự chính xác, quyền sử dụng và claim trước khi xuất bản.",
            "boundaries": _boundaries(),
        },
        status_name="completed",
    )
