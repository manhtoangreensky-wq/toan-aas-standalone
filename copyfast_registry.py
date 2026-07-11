"""Canonical Web-App surface for the COPYFAST compatibility layer.

This module deliberately contains no provider implementation.  It is the one
place the web shell, API and migration inventory use to decide which public
route corresponds to a bot capability.  Runtime readiness always comes from
the private bot bridge; a catalog entry is never evidence that an engine works.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class WebFeature:
    key: str
    title: str
    group: str
    route: str
    kind: str = "customer"
    description: str = ""
    input_hint: str = ""


CUSTOMER_FEATURES: tuple[WebFeature, ...] = (
    WebFeature("dashboard", "Tổng quan", "account", "/dashboard", description="Tài khoản, Xu, job và trạng thái gần đây."),
    WebFeature("feature_catalog", "Tất cả công cụ", "content", "/features", description="Khám phá các workflow Web đã được định tuyến và trạng thái canonical của chúng."),
    WebFeature("account", "Tài khoản", "account", "/account", description="Hồ sơ, liên kết Telegram và bảo mật."),
    WebFeature("wallet", "Ví Xu", "wallet", "/wallet", description="Số dư và lịch sử canonical từ bot."),
    WebFeature("wallet_topup", "Nạp Xu", "wallet", "/wallet/topup", description="Tạo thanh toán qua core PayOS canonical."),
    WebFeature("packages", "Gói dịch vụ", "wallet", "/packages"),
    WebFeature("jobs", "Công việc", "jobs", "/jobs", description="Theo dõi trạng thái và kết quả đã xác thực."),
    WebFeature("assets", "Tài sản", "jobs", "/assets", description="Tệp đầu ra thuộc quyền sở hữu của bạn."),
    WebFeature("chat", "Chat AI", "content", "/chat", input_hint="Nhập yêu cầu hoặc bối cảnh."),
    WebFeature("prompt_studio", "Prompt Studio", "content", "/prompt-studio", input_hint="Mô tả mục tiêu nội dung."),
    WebFeature("caption", "Caption", "content", "/content/caption"),
    WebFeature("hashtag", "Hashtag", "content", "/content/hashtag"),
    WebFeature("hook", "Hook", "content", "/content/hook"),
    WebFeature("script", "Kịch bản", "content", "/content/script"),
    WebFeature("storyboard", "Storyboard", "content", "/content/storyboard"),
    WebFeature("content_pack", "Content Pack", "content", "/content/pack"),
    WebFeature("image_create", "Tạo ảnh", "image", "/image/create", input_hint="Prompt ảnh và tỉ lệ khung hình."),
    WebFeature("image_edit", "Chỉnh sửa ảnh", "image", "/image/edit", input_hint="Tải ảnh và mô tả chỉnh sửa."),
    WebFeature("image_upscale", "Nâng cấp ảnh", "image", "/image/upscale", input_hint="Tải ảnh cần upscale."),
    WebFeature("image_transform", "Image-to-image", "image", "/image/transform", input_hint="Ảnh nguồn và mô tả biến thể."),
    WebFeature("image_remove_background", "Xóa nền", "image", "/image/remove-background", input_hint="Tải ảnh cần xử lý."),
    WebFeature("image_history", "Lịch sử ảnh", "image", "/image/history"),
    WebFeature("video_single", "Video nhanh", "video", "/video/create", input_hint="Prompt hoặc brief video."),
    WebFeature("video_image_to_video", "Ảnh thành video", "video", "/video/image-to-video", input_hint="Ảnh nguồn và chuyển động mong muốn."),
    WebFeature("video_product", "Video sản phẩm", "video", "/video/product", input_hint="Thông tin sản phẩm và hình ảnh."),
    WebFeature("video_trend", "Video theo trend", "video", "/video/trend", input_hint="Trend hoặc tham chiếu an toàn."),
    WebFeature("video_text_to_video", "Text-to-video", "video", "/video/text-to-video", input_hint="Prompt video và tham số đã xác minh."),
    WebFeature("video_quick", "Quick video", "video", "/video/quick", input_hint="Brief video ngắn."),
    WebFeature("video_multiscene", "Video nhiều cảnh", "video", "/video/multiscene", input_hint="Brief, cảnh và giọng đọc."),
    WebFeature("video_long", "Video dài", "video", "/video/long", input_hint="Dự án video dài."),
    WebFeature("video_progress", "Tiến độ video", "video", "/video/progress"),
    WebFeature("video_preview", "Xem trước video", "video", "/video/preview"),
    WebFeature("video_export", "Xuất video", "video", "/video/export"),
    WebFeature("video_addons", "Video add-ons", "video", "/video/add-ons"),
    WebFeature("video_mux", "Mux audio/video", "video", "/video/mux"),
    WebFeature("voice_tts", "Giọng đọc", "voice", "/voice/create", input_hint="Văn bản và giọng đọc."),
    WebFeature("voice_clone", "Clone giọng", "voice", "/voice/clone", input_hint="Mẫu âm thanh đã được phép sử dụng."),
    WebFeature("voice_saved_tts", "Giọng đã lưu", "voice", "/voice/saved", input_hint="Chọn voice vault."),
    WebFeature("voice_vault", "Voice vault", "voice", "/voice"),
    WebFeature("voice_preview", "Nghe thử giọng", "voice", "/voice/preview"),
    WebFeature("voice_outputs", "Voice outputs", "voice", "/voice/outputs"),
    WebFeature("music_library", "Thư viện nhạc", "music", "/music/library"),
    WebFeature("sfx_library", "Thư viện SFX", "music", "/music/sfx-library", description="Tài sản hiệu ứng âm thanh thuộc phiên đã được Core Bridge xác minh."),
    WebFeature("music_background", "Nhạc nền AI", "music", "/music/ai", input_hint="Phong cách, mood và thời lượng."),
    WebFeature("music_song", "Bài hát AI", "music", "/music/song", input_hint="Lời, phong cách và chế độ half/full."),
    WebFeature("music_sfx", "SFX", "music", "/music/sfx", input_hint="Brief hiệu ứng âm thanh."),
    WebFeature("music_upload", "Nhạc của tôi", "music", "/music/upload"),
    WebFeature("subtitle_asr", "Tạo phụ đề", "subtitle", "/subtitle", input_hint="Tải video hoặc audio."),
    WebFeature("subtitle_create", "Tạo phụ đề", "subtitle", "/subtitle/create", input_hint="Tải video hoặc audio."),
    WebFeature("subtitle_translate", "Dịch phụ đề", "subtitle", "/translate", input_hint="Tải SRT/VTT hoặc nhập văn bản."),
    WebFeature("video_dub", "Lồng tiếng", "subtitle", "/dubbing", input_hint="Media nguồn, ngôn ngữ và giọng đọc."),
    WebFeature("asr", "Nhận dạng giọng nói", "subtitle", "/asr", input_hint="Tải audio hoặc video."),
    WebFeature("subtitle_formats", "SRT/VTT", "subtitle", "/subtitle/formats"),
    WebFeature("documents", "Tài liệu & PDF", "documents", "/documents", input_hint="Tải tài liệu để chọn công cụ."),
    WebFeature("documents_pdf", "PDF tools", "documents", "/documents/pdf"),
    WebFeature("documents_ocr", "OCR", "documents", "/documents/ocr"),
    WebFeature("documents_merge", "Gộp tài liệu", "documents", "/documents/merge"),
    WebFeature("documents_split", "Tách tài liệu", "documents", "/documents/split"),
    WebFeature("documents_compress", "Nén tài liệu", "documents", "/documents/compress"),
    WebFeature("documents_translate", "Dịch tài liệu", "documents", "/documents/translate"),
    WebFeature("support", "Hỗ trợ", "support", "/support"),
    WebFeature("tickets", "Phiếu hỗ trợ", "support", "/tickets"),
    WebFeature("pricing", "Bảng giá", "support", "/pricing"),
    WebFeature("legal", "Điều khoản", "support", "/legal"),
    WebFeature("privacy", "Quyền riêng tư", "support", "/privacy"),
)

ADMIN_FEATURES: tuple[WebFeature, ...] = (
    WebFeature("admin_overview", "Tổng quan vận hành", "admin", "/admin", "admin"),
    WebFeature("admin_users", "Người dùng", "admin", "/admin/users", "admin"),
    WebFeature("admin_wallet", "Ví & Xu", "admin", "/admin/wallet", "admin"),
    WebFeature("admin_payments", "Thanh toán", "admin", "/admin/payments", "admin"),
    WebFeature("admin_topups", "Nạp Xu", "admin", "/admin/topups", "admin"),
    WebFeature("admin_revenue", "Doanh thu", "admin", "/admin/revenue", "admin"),
    WebFeature("admin_jobs", "Jobs", "admin", "/admin/jobs", "admin"),
    WebFeature("admin_refunds", "Hoàn tiền", "admin", "/admin/refunds", "admin"),
    WebFeature("admin_providers", "Nhà cung cấp", "admin", "/admin/providers", "admin"),
    WebFeature("admin_provider_cost", "Chi phí provider", "admin", "/admin/provider-cost", "admin"),
    WebFeature("admin_workers", "Workers", "admin", "/admin/workers", "admin"),
    WebFeature("admin_features", "Readiness", "admin", "/admin/features", "admin"),
    WebFeature("admin_freezes", "Bảo trì & freeze", "admin", "/admin/freezes", "admin"),
    WebFeature("admin_pricing", "Giá & gói", "admin", "/admin/pricing", "admin"),
    WebFeature("admin_promos", "Khuyến mãi", "admin", "/admin/promos", "admin"),
    WebFeature("admin_leads", "Leads", "admin", "/admin/leads", "admin"),
    WebFeature("admin_tickets", "CSKH", "admin", "/admin/tickets", "admin"),
    WebFeature("admin_audit", "Nhật ký audit", "admin", "/admin/audit", "admin"),
    WebFeature("admin_reports", "Báo cáo", "admin", "/admin/reports", "admin"),
    WebFeature("admin_system", "Hệ thống", "admin", "/admin/system", "admin"),
    WebFeature("admin_runtime", "Runtime", "admin", "/admin/runtime", "admin"),
    WebFeature("admin_backups", "Sao lưu", "admin", "/admin/backups", "admin"),
)

ALL_FEATURES: tuple[WebFeature, ...] = CUSTOMER_FEATURES + ADMIN_FEATURES
FEATURE_BY_KEY = {item.key: item for item in ALL_FEATURES}


def catalog() -> list[dict[str, str]]:
    return [asdict(item) for item in ALL_FEATURES]


def allowed_paths() -> set[str]:
    result = {"/", "/login", "/register", "/onboarding"}
    for item in ALL_FEATURES:
        result.add(item.route.split("?", 1)[0])
    return result


def feature_keys() -> Iterable[str]:
    return FEATURE_BY_KEY.keys()
