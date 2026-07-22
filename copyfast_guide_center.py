"""Signed, read-only Guide Center for the standalone TOAN AAS Web App.

The frozen Telegram Bot is an audit reference only.  This module contains a
small, reviewed Web snapshot so the browser never imports Bot code, opens Bot
files, replays Telegram callbacks, or depends on a Bot conversation.  It is a
navigation and education surface only: it does not call a provider or bridge,
create a job, mutate a wallet, begin payment, persist an asset, publish
content, or deliver media.

The route catalog is intentionally closed.  A future content edit must add a
route here deliberately rather than turning this page into a generic redirect
or a way to surface privileged/internal destinations.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from fastapi import APIRouter, Depends, Response

from copyfast_auth import envelope, normalize_interface_locale, require_account


router = APIRouter(prefix="/api/v1/guides", tags=["Web Guide Center"])

SNAPSHOT_VERSION = "2026-07-22.1"
LOCALES = frozenset({"vi", "en", "zh"})
TOPIC_IDS = frozenset(
    {
        "getting_started",
        "find_tools",
        "content_brief",
        "prompt_library",
        "image_preparation",
        "audio_brief",
        "notes",
        "reminders",
        "safe_workspace",
        "get_support",
    }
)

# The Guide Center is customer-facing and deliberately excludes wallet/top-up,
# admin, API/internal, provider, Bot and arbitrary external destinations.
ROUTE_ALLOWLIST = frozenset(
    {
        "/onboarding",
        "/workspace-setup",
        "/features",
        "/content-studio",
        "/prompt-library",
        "/image-studio",
        "/media-workspace",
        "/notes",
        "/reminders",
        "/guides/source-rights",
        "/account/security",
        "/support",
    }
)


@dataclass(frozen=True)
class GuideGroup:
    id: str
    translations: Mapping[str, Mapping[str, str]]


@dataclass(frozen=True)
class GuideTopic:
    id: str
    group_id: str
    route: str
    availability: str
    translations: Mapping[str, Mapping[str, Any]]


def _localized(**values: Mapping[str, Any]) -> Mapping[str, Mapping[str, Any]]:
    """Freeze a complete vi/en/zh localizable payload at module load time."""

    if set(values) != LOCALES:
        raise RuntimeError("Guide Center translations must define exactly vi/en/zh")
    return MappingProxyType({locale: MappingProxyType(dict(value)) for locale, value in values.items()})


GROUPS: tuple[GuideGroup, ...] = (
    GuideGroup(
        "start",
        _localized(
            vi={"title": "Bắt đầu", "summary": "Thiết lập không gian làm việc và chọn đúng công cụ."},
            en={"title": "Get started", "summary": "Set up your workspace and choose the right tool."},
            zh={"title": "开始使用", "summary": "设置工作区并选择合适的工具。"},
        ),
    ),
    GuideGroup(
        "create",
        _localized(
            vi={"title": "Tạo nội dung", "summary": "Bắt đầu từ brief rõ ràng và giữ prompt có thể tái sử dụng."},
            en={"title": "Create content", "summary": "Start with a clear brief and keep reusable prompts."},
            zh={"title": "创作内容", "summary": "从清晰的简报开始，并保留可复用的提示词。"},
        ),
    ),
    GuideGroup(
        "media",
        _localized(
            vi={"title": "Ảnh & âm thanh", "summary": "Chuẩn bị nguồn tư liệu, direction và quyền sử dụng trước khi chạy workflow."},
            en={"title": "Images & audio", "summary": "Prepare source material, direction and usage rights before a workflow."},
            zh={"title": "图片与音频", "summary": "在开始工作流前准备素材、方向和使用权。"},
        ),
    ),
    GuideGroup(
        "organize",
        _localized(
            vi={"title": "Tổ chức công việc", "summary": "Lưu ý tưởng, ưu tiên việc quan trọng và theo dõi nhịp làm việc."},
            en={"title": "Organize work", "summary": "Capture ideas, prioritize important work and keep momentum."},
            zh={"title": "组织工作", "summary": "记录想法、安排优先级并保持工作节奏。"},
        ),
    ),
    GuideGroup(
        "safe",
        _localized(
            vi={"title": "An toàn & hỗ trợ", "summary": "Bảo vệ tài khoản, kiểm tra nguồn và nhận trợ giúp đúng kênh."},
            en={"title": "Safety & support", "summary": "Protect your account, check sources and get help through the right channel."},
            zh={"title": "安全与支持", "summary": "保护账户、核查素材来源，并通过正确渠道获得帮助。"},
        ),
    ),
)


UI_COPY = _localized(
    vi={
        "kicker": "Web-native · chỉ đọc",
        "heading": "Tìm đúng bước tiếp theo, không cần nhớ lệnh.",
        "body": "Guide Center tổ chức các bước chuẩn bị và đường dẫn workspace theo tài khoản Web hiện tại. Nội dung không chạy công cụ, không tạo job hay thay đổi dữ liệu thanh toán.",
        "search_label": "Tìm trong Guide Center",
        "search_placeholder": "Tìm theo mục tiêu, công cụ hoặc việc cần làm…",
        "search_help": "Tìm kiếm chỉ lọc các thẻ đang có trên trang này; không gửi từ khóa lên máy chủ hoặc lưu vào trình duyệt.",
        "result_count": "{count} chủ đề phù hợp",
        "all_count": "{count} chủ đề",
        "topic_count_label": "chủ đề",
        "execution_count": "Không có thực thi",
        "empty_title": "Không tìm thấy chủ đề phù hợp",
        "empty_body": "Thử một từ ngắn hơn hoặc xem lại tất cả nhóm hướng dẫn.",
        "static_badge": "Hướng dẫn",
        "availability_badge": "Kiểm tra trong workspace",
        "steps": "Các bước gợi ý",
        "boundary_title": "Hướng dẫn, không phải thực thi",
        "boundary_body": "Guide Center không gọi Bot, bridge, provider, job, wallet, payment, asset, publish hoặc delivery. Mỗi workspace vẫn tự kiểm tra quyền và trạng thái hiện tại.",
    },
    en={
        "kicker": "Web-native · read-only",
        "heading": "Find the next right step without remembering commands.",
        "body": "Guide Center organizes preparation steps and workspace routes for the current Web account. It does not run a tool, create a job or change payment data.",
        "search_label": "Search Guide Center",
        "search_placeholder": "Search by goal, tool or task…",
        "search_help": "Search only filters the cards already on this page; it is not sent to the server or saved in the browser.",
        "result_count": "{count} matching topics",
        "all_count": "{count} topics",
        "topic_count_label": "topics",
        "execution_count": "No execution",
        "empty_title": "No matching topic found",
        "empty_body": "Try a shorter term or browse all guide groups again.",
        "static_badge": "Guide",
        "availability_badge": "Check in workspace",
        "steps": "Suggested steps",
        "boundary_title": "Guidance, not execution",
        "boundary_body": "Guide Center does not call a Bot, bridge, provider, job, wallet, payment, asset, publish or delivery flow. Each workspace still checks its own access and current state.",
    },
    zh={
        "kicker": "Web 原生 · 只读",
        "heading": "无需记住命令，也能找到正确的下一步。",
        "body": "Guide Center 为当前 Web 账户整理准备步骤和工作区路径。它不会运行工具、创建任务或更改支付数据。",
        "search_label": "搜索 Guide Center",
        "search_placeholder": "按目标、工具或任务搜索…",
        "search_help": "搜索仅筛选当前页面上的卡片；不会发送到服务器，也不会保存在浏览器中。",
        "result_count": "{count} 个匹配主题",
        "all_count": "{count} 个主题",
        "topic_count_label": "个主题",
        "execution_count": "不执行",
        "empty_title": "未找到匹配主题",
        "empty_body": "请尝试更短的关键词，或重新浏览所有指南分组。",
        "static_badge": "指南",
        "availability_badge": "在工作区检查",
        "steps": "建议步骤",
        "boundary_title": "指南，不是执行",
        "boundary_body": "Guide Center 不调用 Bot、bridge、provider、job、wallet、payment、asset、publish 或 delivery 流程。每个工作区仍会自行检查权限和当前状态。",
    },
)


TOPICS: tuple[GuideTopic, ...] = (
    GuideTopic(
        "getting_started",
        "start",
        "/onboarding",
        "static",
        _localized(
            vi={
                "title": "Thiết lập lần đầu",
                "summary": "Hoàn tất hồ sơ và chọn một điểm bắt đầu phù hợp với công việc của bạn.",
                "steps": ("Kiểm tra thông tin tài khoản.", "Chọn mục tiêu làm việc đầu tiên.", "Lưu thay đổi trước khi mở studio."),
                "route_label": "Mở thiết lập",
            },
            en={
                "title": "Set up for the first time",
                "summary": "Complete your profile and choose a starting point that fits your work.",
                "steps": ("Check your account details.", "Choose your first workspace goal.", "Save changes before opening a studio."),
                "route_label": "Open setup",
            },
            zh={
                "title": "首次设置",
                "summary": "完成个人资料，并选择适合你工作的起点。",
                "steps": ("检查账户信息。", "选择第一个工作目标。", "进入工作室前保存更改。"),
                "route_label": "打开设置",
            },
        ),
    ),
    GuideTopic(
        "find_tools",
        "start",
        "/features",
        "capability_backed",
        _localized(
            vi={
                "title": "Tìm đúng công cụ",
                "summary": "Duyệt theo mục tiêu thay vì thử ngẫu nhiên; mỗi công cụ hiển thị trạng thái riêng của nó.",
                "steps": ("Chọn mục tiêu: nội dung, hình, âm thanh hoặc tài liệu.", "Đọc phạm vi và yêu cầu đầu vào.", "Chỉ tiếp tục khi workspace hiển thị sẵn sàng."),
                "route_label": "Xem công cụ",
            },
            en={
                "title": "Find the right tool",
                "summary": "Browse by goal instead of guessing; each tool shows its own availability.",
                "steps": ("Choose a goal: content, image, audio or document.", "Read the scope and input requirements.", "Continue only when the workspace shows ready."),
                "route_label": "Browse tools",
            },
            zh={
                "title": "选择合适工具",
                "summary": "按目标浏览，而不是随意尝试；每个工具都会显示自己的可用状态。",
                "steps": ("选择目标：内容、图片、音频或文档。", "阅读范围和输入要求。", "仅在工作区显示可用时继续。"),
                "route_label": "查看工具",
            },
        ),
    ),
    GuideTopic(
        "content_brief",
        "create",
        "/content-studio",
        "capability_backed",
        _localized(
            vi={
                "title": "Viết brief đủ rõ",
                "summary": "Một brief tốt giúp bạn review ý tưởng trước khi chuyển sang bước tiếp theo.",
                "steps": ("Nêu đối tượng và mục tiêu.", "Ghi thông điệp, ràng buộc và CTA.", "Rà lại bản nháp trong Content Studio."),
                "route_label": "Mở Content Studio",
            },
            en={
                "title": "Write a clear brief",
                "summary": "A clear brief helps you review an idea before moving to the next step.",
                "steps": ("State the audience and goal.", "Add the message, constraints and CTA.", "Review the draft in Content Studio."),
                "route_label": "Open Content Studio",
            },
            zh={
                "title": "写清晰简报",
                "summary": "清晰的简报可帮助你在进入下一步前审核想法。",
                "steps": ("说明受众和目标。", "添加信息、限制条件和 CTA。", "在 Content Studio 中审核草稿。"),
                "route_label": "打开 Content Studio",
            },
        ),
    ),
    GuideTopic(
        "prompt_library",
        "create",
        "/prompt-library",
        "capability_backed",
        _localized(
            vi={
                "title": "Lưu prompt có cấu trúc",
                "summary": "Tách prompt dùng lại khỏi ý tưởng một lần để dễ tìm và cải thiện theo thời gian.",
                "steps": ("Đặt tên theo mục tiêu.", "Ghi context và biến cần thay đổi.", "Review trước khi dùng lại cho dự án mới."),
                "route_label": "Mở Prompt Library",
            },
            en={
                "title": "Keep structured prompts",
                "summary": "Separate reusable prompts from one-off ideas so they stay findable and improve over time.",
                "steps": ("Name it by its goal.", "Record the context and variables.", "Review it before reusing it in a new project."),
                "route_label": "Open Prompt Library",
            },
            zh={
                "title": "保存结构化提示词",
                "summary": "将可复用提示词与一次性想法分开，方便查找并持续改进。",
                "steps": ("按目标命名。", "记录上下文和可变参数。", "在新项目复用前先审核。"),
                "route_label": "打开 Prompt Library",
            },
        ),
    ),
    GuideTopic(
        "image_preparation",
        "media",
        "/image-studio",
        "capability_backed",
        _localized(
            vi={
                "title": "Chuẩn bị ảnh",
                "summary": "Mô tả chủ thể, bố cục, tỷ lệ và điều không được thay đổi trước khi bắt đầu.",
                "steps": ("Xác định mục tiêu sử dụng và tỷ lệ khung hình.", "Viết rõ chủ thể, bối cảnh và style.", "Kiểm tra workspace để biết tính năng đang khả dụng."),
                "route_label": "Mở Image Studio",
            },
            en={
                "title": "Prepare an image brief",
                "summary": "Describe the subject, composition, ratio and what must not change before you begin.",
                "steps": ("Define the use case and aspect ratio.", "State the subject, context and style clearly.", "Check the workspace for current availability."),
                "route_label": "Open Image Studio",
            },
            zh={
                "title": "准备图片简报",
                "summary": "开始前描述主体、构图、比例以及不可改变的内容。",
                "steps": ("确定用途和画面比例。", "清晰说明主体、场景和风格。", "在工作区查看当前可用性。"),
                "route_label": "打开 Image Studio",
            },
        ),
    ),
    GuideTopic(
        "audio_brief",
        "media",
        "/media-workspace",
        "capability_backed",
        _localized(
            vi={
                "title": "Lập direction âm thanh",
                "summary": "Xác định mood, nhịp và mục đích sử dụng trước khi lưu direction hoặc làm việc với thư viện.",
                "steps": ("Nêu cảm xúc và nhịp mong muốn.", "Ghi ngữ cảnh sử dụng và giới hạn bản quyền.", "Kiểm tra danh sách audio của chính bạn trong workspace."),
                "route_label": "Mở Audio Library",
            },
            en={
                "title": "Plan an audio direction",
                "summary": "Define mood, pacing and intended use before saving a direction or working with the library.",
                "steps": ("State the desired mood and pace.", "Record intended use and rights constraints.", "Check your own audio list in the workspace."),
                "route_label": "Open Audio Library",
            },
            zh={
                "title": "规划音频方向",
                "summary": "在保存方向或使用音频库前，确定情绪、节奏和预期用途。",
                "steps": ("说明所需情绪和节奏。", "记录用途和版权限制。", "在工作区查看自己的音频列表。"),
                "route_label": "打开音频库",
            },
        ),
    ),
    GuideTopic(
        "notes",
        "organize",
        "/notes",
        "capability_backed",
        _localized(
            vi={
                "title": "Ghi chú để dùng lại",
                "summary": "Lưu ý tưởng, context và quyết định để lần sau không phải bắt đầu lại từ đầu.",
                "steps": ("Tạo tiêu đề ngắn, dễ tìm.", "Gắn tag và ưu tiên phù hợp.", "Archive nội dung đã xong thay vì xóa thông tin hữu ích."),
                "route_label": "Mở Memory Center",
            },
            en={
                "title": "Capture reusable notes",
                "summary": "Keep ideas, context and decisions so the next session does not start from zero.",
                "steps": ("Create a short, searchable title.", "Add useful tags and priority.", "Archive completed material instead of losing useful context."),
                "route_label": "Open Memory Center",
            },
            zh={
                "title": "记录可复用笔记",
                "summary": "保存想法、上下文和决定，让下一次工作无需从零开始。",
                "steps": ("创建简短、易搜索的标题。", "添加有用的标签和优先级。", "完成后归档，而不是丢失有价值的上下文。"),
                "route_label": "打开 Memory Center",
            },
        ),
    ),
    GuideTopic(
        "reminders",
        "organize",
        "/reminders",
        "capability_backed",
        _localized(
            vi={
                "title": "Theo dõi việc quan trọng",
                "summary": "Dùng reminder Web để sắp xếp việc cá nhân; không giả định có thông báo bên ngoài.",
                "steps": ("Viết việc cần làm thật cụ thể.", "Đặt mốc thời gian và nhịp lặp phù hợp.", "Pause, complete hoặc archive khi trạng thái thay đổi."),
                "route_label": "Mở Nhắc việc",
            },
            en={
                "title": "Track important work",
                "summary": "Use Web reminders to organize personal work; do not assume an external notification exists.",
                "steps": ("Write a specific next action.", "Set a time and repeat pattern that fits.", "Pause, complete or archive it as the state changes."),
                "route_label": "Open Reminders",
            },
            zh={
                "title": "跟踪重要工作",
                "summary": "使用 Web 提醒整理个人工作；不要假设存在外部通知。",
                "steps": ("写下具体的下一步行动。", "设置合适的时间和重复方式。", "状态变化时暂停、完成或归档。"),
                "route_label": "打开提醒",
            },
        ),
    ),
    GuideTopic(
        "safe_workspace",
        "safe",
        "/account/security",
        "static",
        _localized(
            vi={
                "title": "Giữ workspace an toàn",
                "summary": "Không nhập secret vào brief, review hoạt động tài khoản và dùng đúng quyền của mình.",
                "steps": ("Không đưa mật khẩu, token hoặc thông tin thẻ vào nội dung.", "Dùng một mật khẩu riêng và bảo vệ phiên đăng nhập.", "Kiểm tra trang bảo mật khi thấy hoạt động bất thường."),
                "route_label": "Mở bảo mật tài khoản",
            },
            en={
                "title": "Keep the workspace safe",
                "summary": "Do not put secrets in a brief, review account activity and use only your own permissions.",
                "steps": ("Never put passwords, tokens or card details into content.", "Use a unique password and protect your signed session.", "Review the security page when activity looks unusual."),
                "route_label": "Open account security",
            },
            zh={
                "title": "保护工作区安全",
                "summary": "不要在简报中输入密钥，检查账户活动，并仅使用自己的权限。",
                "steps": ("不要在内容中填写密码、令牌或银行卡信息。", "使用唯一密码并保护已登录会话。", "发现异常活动时检查安全页面。"),
                "route_label": "打开账户安全",
            },
        ),
    ),
    GuideTopic(
        "get_support",
        "safe",
        "/support",
        "capability_backed",
        _localized(
            vi={
                "title": "Nhận hỗ trợ đúng ngữ cảnh",
                "summary": "Gửi mô tả ngắn, bước đã thử và ảnh chụp không chứa dữ liệu nhạy cảm để hỗ trợ xử lý nhanh hơn.",
                "steps": ("Nêu mục tiêu và điều đang xảy ra.", "Ghi các bước đã thử và thời điểm gặp lỗi.", "Ẩn password, token, hóa đơn hoặc dữ liệu cá nhân trước khi gửi."),
                "route_label": "Mở Hỗ trợ",
            },
            en={
                "title": "Get support with context",
                "summary": "Send a short description, the steps tried and a non-sensitive screenshot to help support respond faster.",
                "steps": ("State the goal and what is happening.", "Include the steps tried and when it happened.", "Remove passwords, tokens, invoices and personal data before sending."),
                "route_label": "Open Support",
            },
            zh={
                "title": "带着上下文获得支持",
                "summary": "发送简短描述、已尝试步骤和不含敏感信息的截图，以便支持更快响应。",
                "steps": ("说明目标和当前现象。", "写明已尝试步骤和发生时间。", "发送前移除密码、令牌、账单和个人数据。"),
                "route_label": "打开支持",
            },
        ),
    ),
)


def _private_no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Vary"] = "Cookie"


def _copy_text(value: object, *, limit: int = 240) -> str:
    text = str(value or "").strip()
    if not text or len(text) > limit or any(ord(character) < 32 for character in text):
        raise RuntimeError("Guide Center snapshot contains unsafe text")
    return text


def _public_topic(topic: GuideTopic, locale: str) -> dict[str, Any]:
    if topic.id not in TOPIC_IDS or topic.route not in ROUTE_ALLOWLIST:
        raise RuntimeError("Guide Center snapshot contains an unsupported topic or route")
    if topic.availability not in {"static", "capability_backed"}:
        raise RuntimeError("Guide Center snapshot contains an unsupported availability")
    copy = topic.translations[locale]
    steps = copy.get("steps")
    if not isinstance(steps, tuple) or not 2 <= len(steps) <= 4:
        raise RuntimeError("Guide Center topic steps must be a short immutable list")
    return {
        "id": topic.id,
        "title": _copy_text(copy.get("title"), limit=100),
        "summary": _copy_text(copy.get("summary")),
        "steps": [_copy_text(step, limit=220) for step in steps],
        "route": topic.route,
        "route_label": _copy_text(copy.get("route_label"), limit=100),
        "availability": topic.availability,
    }


def guide_catalog(locale: object) -> dict[str, Any]:
    """Return a fresh JSON-safe catalog using only the signed profile locale."""

    selected_locale = normalize_interface_locale(locale)
    if selected_locale not in LOCALES:
        selected_locale = "vi"
    topics_by_group: dict[str, list[GuideTopic]] = {group.id: [] for group in GROUPS}
    for topic in TOPICS:
        if topic.group_id not in topics_by_group:
            raise RuntimeError("Guide Center topic points to an unknown group")
        topics_by_group[topic.group_id].append(topic)
    groups = []
    for group in GROUPS:
        copy = group.translations[selected_locale]
        groups.append(
            {
                "id": group.id,
                "title": _copy_text(copy.get("title"), limit=80),
                "summary": _copy_text(copy.get("summary")),
                "topics": [_public_topic(topic, selected_locale) for topic in topics_by_group[group.id]],
            }
        )
    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "locale": selected_locale,
        "description": {
            "vi": "Hướng dẫn Web-native được biên soạn để bắt đầu an toàn và tìm đúng workspace.",
            "en": "A Web-native guide for getting started safely and finding the right workspace.",
            "zh": "面向 Web 的指南，帮助你安全开始并找到合适的工作区。",
        }[selected_locale],
        "ui": {key: _copy_text(value, limit=360) for key, value in UI_COPY[selected_locale].items()},
        "groups": groups,
        "boundaries": {
            "execution": "web_native_guide_center",
            "snapshot_read_only": True,
            "bot_called": False,
            "bridge_called": False,
            "provider_called": False,
            "job_created": False,
            "wallet_mutated": False,
            "payment_started": False,
            "asset_saved": False,
            "content_published": False,
            "media_delivered": False,
        },
    }


@router.get("/catalog")
def get_catalog(response: Response, account: dict[str, Any] = Depends(require_account)) -> dict[str, Any]:
    """Return only the reviewed guide snapshot for a signed Web account."""

    _private_no_store(response)
    return envelope(
        True,
        "Đã tải Guide Center Web-native chỉ đọc.",
        data=guide_catalog(account.get("locale")),
        status_name="completed",
    )
